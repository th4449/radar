"""Load and validate the YAML files in config/.

Every file has a strict schema. An unknown key or a bad value fails loudly, because a typo in
a source entry or a scoring weight would otherwise change behavior without anyone noticing.
"""

from __future__ import annotations

import datetime as dt
import re
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"

State = Literal["TX", "MI", "US"]
Method = Literal["http", "browser", "manual"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


# --- sources.yaml -----------------------------------------------------------------------------


class Source(_Strict):
    id: str = Field(pattern=r"^(tx|mi|us)_[a-z0-9_]+$")
    state: State
    name: str = Field(min_length=3)
    url: HttpUrl
    layer: Literal["signal", "context", "baseline", "lookup"]
    method: Method
    intended_method: Literal["http", "browser", "manual", "unknown"]
    cadence: Literal["daily", "weekly", "monthly", "yearly", "once", "on_demand"]
    robots_status: Literal["not_checked", "allowed", "restricted", "blocked"]
    verified_at: dt.date | None
    # Raises the fetcher's 50 MB limit for this source. Set it only for a known large file.
    max_body_mb: int | None = Field(default=None, ge=51, le=500)
    # The source is a list that names people, such as permit applicants or well owners. Its
    # documents are stored restricted: an administrator reads them, a reviewer does not.
    personal_rows: bool = False
    notes: str = ""

    @model_validator(mode="after")
    def _automation_needs_verification(self) -> Source:
        """A source may be automated only after its terms and robots rules were checked."""
        if self.method != "manual":
            if self.verified_at is None:
                raise ValueError(f"{self.id}: method {self.method} needs verified_at")
            if self.robots_status != "allowed":
                raise ValueError(f"{self.id}: method {self.method} needs robots_status allowed")
        if not self.id.startswith(self.state.lower() + "_"):
            raise ValueError(f"{self.id}: id prefix does not match state {self.state}")
        return self

    @property
    def may_fetch_automatically(self) -> bool:
        return self.method != "manual"


class SourcesFile(_Strict):
    sources: list[Source]

    @field_validator("sources")
    @classmethod
    def _unique_ids(cls, v: list[Source]) -> list[Source]:
        ids = [s.id for s in v]
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        if dupes:
            raise ValueError(f"duplicate source ids: {dupes}")
        return v

    def by_id(self, source_id: str) -> Source:
        for s in self.sources:
            if s.id == source_id:
                return s
        raise KeyError(source_id)


# --- counties_*.yaml --------------------------------------------------------------------------


class County(_Strict):
    name: str
    fips: str = Field(pattern=r"^\d{5}$")
    group: Literal["ranked_25", "activity_5"] | None = None
    agenda_priority: int | None = None


class CountiesFile(_Strict):
    state: Literal["TX", "MI"]
    counties: list[County]

    @model_validator(mode="after")
    def _check(self) -> CountiesFile:
        prefix = {"TX": "48", "MI": "26"}[self.state]
        fips = [c.fips for c in self.counties]
        if len(set(fips)) != len(fips):
            raise ValueError("duplicate county FIPS codes")
        bad = [c.name for c in self.counties if not c.fips.startswith(prefix)]
        if bad:
            raise ValueError(f"FIPS codes outside {self.state}: {bad}")
        return self

    @property
    def fips_set(self) -> frozenset[str]:
        return frozenset(c.fips for c in self.counties)


# --- keywords.yaml ----------------------------------------------------------------------------


class ProjectCodeName(_Strict):
    pattern: str
    project_stoplist: list[str]

    @field_validator("pattern")
    @classmethod
    def _compiles(cls, v: str) -> str:
        re.compile(v)
        return v


class KeywordsFile(_Strict):
    direct_terms: list[str] = Field(min_length=1)
    code_words: list[str] = Field(min_length=1)
    project_code_name: ProjectCodeName

    @model_validator(mode="after")
    def _lowercase_and_distinct(self) -> KeywordsFile:
        terms = self.direct_terms + self.code_words
        if any(t != t.lower().strip() for t in terms):
            raise ValueError("terms must be lowercase with no surrounding spaces")
        if len(set(terms)) != len(terms):
            raise ValueError("a term appears twice")
        return self


# --- entities.yaml ----------------------------------------------------------------------------


class EntitiesFile(_Strict):
    known_organizations: list[str]
    ordinary_words_on_the_list: list[str]

    @field_validator("known_organizations", "ordinary_words_on_the_list")
    @classmethod
    def _distinct(cls, v: list[str]) -> list[str]:
        if any(not name.strip() for name in v):
            raise ValueError("an empty name")
        if len(set(v)) != len(v):
            raise ValueError("a name appears twice")
        return v


# --- triage.yaml ------------------------------------------------------------------------------


class TriageFile(_Strict):
    model: str = Field(pattern=r"^claude-[a-z0-9-]+$")
    prices_checked: dt.date
    input_per_mtok: float = Field(gt=0)
    output_per_mtok: float = Field(gt=0)
    long_prompt_tokens: int = Field(gt=0)
    long_input_per_mtok: float = Field(gt=0)
    long_output_per_mtok: float = Field(gt=0)
    max_excerpt_chars: int = Field(ge=200, le=50_000)
    max_output_tokens: int = Field(ge=256, le=16_000)
    effort: Literal["low", "medium", "high"]
    prompt_version: int = Field(ge=1)

    @model_validator(mode="after")
    def _long_rates_are_not_cheaper(self) -> TriageFile:
        if self.long_input_per_mtok < self.input_per_mtok:
            raise ValueError("the long prompt input rate is below the base rate")
        if self.long_output_per_mtok < self.output_per_mtok:
            raise ValueError("the long prompt output rate is below the base rate")
        return self


# --- scoring.yaml -----------------------------------------------------------------------------


class SignalType(_Strict):
    weight: Literal["high", "medium", "low"]
    points: float = Field(gt=0)
    half_life_days: int = Field(gt=0)


class MultiSignalBonus(_Strict):
    min_signal_types: int = Field(ge=2)
    window_days: int = Field(gt=0)
    points: float = Field(ge=0)


class Thresholds(_Strict):
    review_threshold: float = Field(gt=0)


RULES = ("direct_term", "listed_company", "listed_company_loose", "project_code_name", "code_word")


class ScoringFile(_Strict):
    placeholder: bool
    signal_types: dict[str, SignalType]
    confidence: dict[str, float]
    multi_signal_bonus: MultiSignalBonus
    thresholds: Thresholds

    @model_validator(mode="after")
    def _weights_are_ordered(self) -> ScoringFile:
        """High must outscore medium, and medium must outscore low."""
        if set(self.confidence) != set(RULES):
            raise ValueError(f"confidence must name exactly these rules: {RULES}")
        if any(not 0 < value <= 1 for value in self.confidence.values()):
            raise ValueError("a confidence is a number above 0 and at most 1")
        if self.confidence["direct_term"] < max(self.confidence.values()):
            raise ValueError("no rule may be surer than a direct term")
        by_weight: dict[str, list[float]] = {"high": [], "medium": [], "low": []}
        for st in self.signal_types.values():
            by_weight[st.weight].append(st.points)
        if (
            by_weight["high"]
            and by_weight["medium"]
            and min(by_weight["high"]) <= max(by_weight["medium"])
        ):
            raise ValueError("a high signal must score above every medium signal")
        if (
            by_weight["medium"]
            and by_weight["low"]
            and min(by_weight["medium"]) <= max(by_weight["low"])
        ):
            raise ValueError("a medium signal must score above every low signal")
        return self


# --- loaders ----------------------------------------------------------------------------------


def _read(name: str, config_dir: Path | None = None) -> dict:
    path = (config_dir or CONFIG_DIR) / name
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must hold a mapping at the top level")
    return data


def load_sources(config_dir: Path | None = None) -> SourcesFile:
    return SourcesFile.model_validate(_read("sources.yaml", config_dir))


def load_counties(state: Literal["TX", "MI"], config_dir: Path | None = None) -> CountiesFile:
    return CountiesFile.model_validate(_read(f"counties_{state.lower()}.yaml", config_dir))


def load_all_counties(state: Literal["TX", "MI"], config_dir: Path | None = None) -> CountiesFile:
    """Every county in the state. Michigan's scope file already holds all of them."""
    name = "counties_tx_all.yaml" if state == "TX" else "counties_mi.yaml"
    return CountiesFile.model_validate(_read(name, config_dir))


def load_keywords(config_dir: Path | None = None) -> KeywordsFile:
    return KeywordsFile.model_validate(_read("keywords.yaml", config_dir))


def load_entities(config_dir: Path | None = None) -> EntitiesFile:
    return EntitiesFile.model_validate(_read("entities.yaml", config_dir))


def load_triage(config_dir: Path | None = None) -> TriageFile:
    return TriageFile.model_validate(_read("triage.yaml", config_dir))


def load_scoring(config_dir: Path | None = None) -> ScoringFile:
    return ScoringFile.model_validate(_read("scoring.yaml", config_dir))
