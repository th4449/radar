import { describe, fitCounties, type Choices, type Frequency } from "../lib/choices";
import { STATES, stateIsRead } from "../lib/places";

interface Props {
  value: Choices;
  onChange: (next: Choices) => void;
}

function toggle(list: string[], item: string, on: boolean): string[] {
  return on ? [...new Set([...list, item])] : list.filter((x) => x !== item);
}

/** States, how often, and the optional county list. Shared by the signup and account pages. */
export function ChoiceFields({ value, onChange }: Props) {
  const set = (patch: Partial<Choices>) => onChange(fitCounties({ ...value, ...patch }));
  const summary = describe(value);

  return (
    <>
      <fieldset>
        <legend>Which states</legend>
        {STATES.map((state) => (
          <label class="inline">
            <input
              type="checkbox"
              checked={value.states.includes(state.code)}
              onChange={(e) =>
                set({
                  states: toggle(value.states, state.code, (e.target as HTMLInputElement).checked),
                })
              }
            />
            <span>
              {state.name}
              {!stateIsRead(state.code) && (
                <span class="note">
                  {" "}
                  No {state.name} record source is read yet. Alerts start when one is.
                </span>
              )}
            </span>
          </label>
        ))}
      </fieldset>

      <fieldset>
        <legend>How often</legend>
        {(
          [
            ["weekly", "A weekly digest for each state. Nothing is sent in a week with no alert."],
            ["each", "An email for each alert, when it is published."],
          ] as [Frequency, string][]
        ).map(([kind, words]) => (
          <label class="inline">
            <input
              type="radio"
              name="frequency"
              checked={value.frequency === kind}
              onChange={() => set({ frequency: kind })}
            />
            <span>{words}</span>
          </label>
        ))}
      </fieldset>

      {STATES.filter((state) => value.states.includes(state.code)).map((state) => {
        const picked = state.counties.filter((c) => value.counties.includes(c.fips)).length;
        return (
          <details>
            <summary>
              Only some {state.name} counties
              {picked > 0 ? ` (${picked} chosen)` : " (optional)"}
            </summary>
            <p class="note">
              Tick none to get every {state.name} alert. The radar watches{" "}
              {state.counties.length} {state.name} counties.
            </p>
            <div class="columns">
              {state.counties.map((county) => (
                <label class="inline">
                  <input
                    type="checkbox"
                    checked={value.counties.includes(county.fips)}
                    onChange={(e) =>
                      set({
                        counties: toggle(
                          value.counties,
                          county.fips,
                          (e.target as HTMLInputElement).checked,
                        ),
                      })
                    }
                  />
                  <span>{county.name}</span>
                </label>
              ))}
            </div>
          </details>
        );
      })}

      {summary && (
        <p aria-live="polite">
          <strong>You will get:</strong> {summary}
        </p>
      )}
    </>
  );
}
