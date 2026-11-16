import { useState } from "react";
import { AiConfig } from "../AiConfig";
import { api, json, type Session } from "../api";
import { TouchButton as Button } from "../TouchButton";
import type { PracticeReport } from "../types/practice";

type Props = {
  session: Session;
  busy: boolean;
  run: (fn: () => Promise<unknown>) => Promise<void>;
  onError: (error: unknown) => void;
  reports: PracticeReport[];
};

export function PracticeReportsPanel({
  session,
  busy,
  run,
  onError,
  reports,
}: Props) {
  const [question, setQuestion] = useState(
    "What should I practise next, based on the available evidence?",
  );
  const [cloud, setCloud] = useState(false);
  const [model, setModel] = useState("gpt-4.1-mini");
  const [reportEdit, setReportEdit] = useState<{
    id: string;
    text: string;
  } | null>(null);
  return (
    <>
      <div className="chart-panel">
        <h2>Your practice report</h2>
        <a
          className="button secondary"
          href={`/api/sessions/${session.id}/preanalysis`}
        >
          Export structured LLM preanalysis (JSON)
        </a>
        <p>
          Local reports use deterministic evidence. Cloud interpretation is
          optional and sends the structured analysis, personal notes and levels,
          recent reports and question to OpenAI, only after the explicit button
          below. It does not upload your score PDFs, MIDI files or audio.
        </p>
        <label>
          Question or follow-up
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            rows={2}
          />
        </label>
        <div className="button-row">
          <Button
            className="primary"
            disabled={busy}
            onClick={() =>
              void run(() =>
                api(
                  `/sessions/${session.id}/teacher`,
                  json("POST", { provider: "local", question }),
                ),
              )
            }
          >
            Generate local report
          </Button>
          <Button className="secondary" onClick={() => setCloud(!cloud)}>
            Optional AI interpretation
          </Button>
        </div>
        {cloud && (
          <div className="info-box">
            <div>
              <AiConfig onError={onError} />
              <label>
                OpenAI model
                <input
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                />
              </label>
              <p>
                Uses OPENAI_API_KEY configured on the backend. Charges and
                provider terms may apply. Review the analysis evidence above
                before sharing.
              </p>
              <Button
                className="secondary"
                disabled={busy}
                onClick={() =>
                  void run(() =>
                    api(
                      `/sessions/${session.id}/teacher`,
                      json("POST", { provider: "openai", model, question }),
                    ),
                  )
                }
              >
                Send analysis evidence to OpenAI
              </Button>
            </div>
          </div>
        )}
        {reports.map((r) => (
          <article className="report" key={r.id}>
            <span className="eyebrow">
              {r.provider} · {new Date(r.created).toLocaleString()}
            </span>
            <div className="report-text">{r.text}</div>
            <Button
              className="secondary"
              onClick={() => setReportEdit({ id: r.id, text: r.text })}
            >
              Edit a new report revision
            </Button>
            <a className="button secondary" href={`/api/reports/${r.id}/text`}>
              Export report
            </a>
          </article>
        ))}
      </div>
      {reportEdit && (
        <div className="chart-panel">
          <label>
            Edit report
            <textarea
              rows={10}
              value={reportEdit.text}
              onChange={(e) =>
                setReportEdit({ ...reportEdit, text: e.target.value })
              }
            />
          </label>
          <Button
            className="primary"
            disabled={busy}
            onClick={() =>
              void run(async () => {
                await api(
                  `/reports/${reportEdit.id}/revision`,
                  json("POST", { text: reportEdit.text }),
                );
                setReportEdit(null);
              })
            }
          >
            Save new report revision
          </Button>
        </div>
      )}
    </>
  );
}
