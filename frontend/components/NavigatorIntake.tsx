"use client";

import { useMutation } from "@tanstack/react-query";
import {
  ArrowRight,
  Bot,
  CheckCircle2,
  Database,
  MapPinned,
  Network,
  Send,
  Sparkles,
  UserRound,
} from "lucide-react";
import { FormEvent, useState } from "react";

import { api } from "@/lib/api";
import type { NavigatorCapabilities, NavigatorIntake, NavigatorMessage } from "@/types/network";

type Props = {
  capabilities?: NavigatorCapabilities;
  onOpenInvestigation: (intake: NavigatorIntake) => void;
};

const quickPrompts = [
  "High loss on DXR-7001 at 18,420 ft from the OTDR launch",
  "Investigate service at 43 Main St (DEV)",
  "Check the serving path for 46 Maple Ave (DEV)",
  "Trace 49 Lake Rd from the LCP splitter port (DEV)",
  "Show outage impact for the backbone cut on DXR-7001",
];

export function NavigatorIntake({ capabilities, onOpenInvestigation }: Props) {
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState<NavigatorMessage[]>([
    {
      role: "assistant",
      content:
        "Describe the circuit, customer location, or OTDR event. I’ll gather the missing details, resolve them against the network system of record, and then open a verified investigation.",
    },
  ]);
  const [result, setResult] = useState<NavigatorIntake | null>(null);
  const intake = useMutation({
    mutationFn: api.navigatorIntake,
    onSuccess: (response) => {
      setResult(response);
      setMessages((current) => {
        const responseMessage: NavigatorMessage = {
          role: "assistant",
          content: response.assistant_message,
        };
        return [...current, responseMessage].slice(-12);
      });
    },
  });

  function send(text: string) {
    const content = text.trim();
    if (!content || intake.isPending) return;
    const userMessage: NavigatorMessage = { role: "user", content };
    const nextMessages: NavigatorMessage[] = [...messages, userMessage].slice(-12);
    setMessages(nextMessages);
    setDraft("");
    intake.mutate(nextMessages);
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    send(draft);
  }

  const aiLive = capabilities?.ai_enabled ?? false;
  const providerLive = capabilities?.network_provider === "vetro" && capabilities.vetro_ready;

  return (
    <section className="navigator-intake">
      <div className="intake-hero">
        <div className="intake-kicker"><Sparkles size={14} /> Investigation intake</div>
        <h2>Start with the signal.<br /><span>Navigator gathers the route.</span></h2>
        <p>
          Tell Photon-Ops what the operator, customer, or OTDR is reporting. The assistant
          structures the request, queries the approved network provider, and hands verified
          data to deterministic fiber analysis.
        </p>

        <div className="intake-pipeline" aria-label="Investigation data pipeline">
          <PipelineNode icon={<UserRound size={17} />} label="Operator" detail="Narrative" active />
          <i />
          <PipelineNode
            icon={<Bot size={17} />}
            label={aiLive ? "Bedrock Mantle" : "Guided parser"}
            detail={aiLive ? "LLM live" : "AI off · demo"}
            active={aiLive}
          />
          <i />
          <PipelineNode
            icon={<Database size={17} />}
            label={capabilities?.network_label ?? "Network provider"}
            detail={capabilities?.network_provider === "vetro" ? (providerLive ? "Connected" : "Profile required") : "Demo PostGIS"}
            active={capabilities?.network_provider === "demo" || providerLive}
          />
          <i />
          <PipelineNode icon={<Network size={17} />} label="Fiber analysis" detail="Deterministic" />
        </div>

        {!aiLive && (
          <div className="intake-notice">
            <Bot size={15} />
            <span><strong>Demo intelligence is active.</strong> Configure Amazon Bedrock Mantle to use LLM interpretation; provider lookups and calculations remain authoritative.</span>
          </div>
        )}
        {!providerLive && (
          <div className="intake-target">
            <MapPinned size={16} />
            <span><strong>Production target · VETRO FiberMap</strong> Customer API profile and token required. No endpoint or schema is being guessed.</span>
          </div>
        )}
      </div>

      <div className="intake-console">
        <div className="intake-console-header">
          <div><span className="assistant-orbit"><Bot size={17} /></span><span><strong>Photon-Ops Navigator</strong><small>{capabilities?.ai_label ?? "Checking capabilities…"}</small></span></div>
          <span className="secure-route">AWS us-east-1</span>
        </div>

        <div className="intake-transcript" aria-live="polite">
          {messages.map((message, index) => (
            <div className={`intake-message ${message.role}`} key={`${message.role}-${index}`}>
              <span>{message.role === "assistant" ? <Bot size={14} /> : <UserRound size={14} />}</span>
              <p>{message.content}</p>
            </div>
          ))}
          {intake.isPending && (
            <div className="intake-message assistant pending"><span><Bot size={14} /></span><p>Resolving the request against the network provider…</p></div>
          )}
        </div>

        {result && (
          <div className={`intake-resolution ${result.status}`}>
            <div>
              <span className="resolution-status">
                {result.status === "ready" ? <CheckCircle2 size={14} /> : <Database size={14} />}
                {result.status === "ready" ? "Verified input" : result.status.replaceAll("_", " ")}
              </span>
              <strong>{result.selected_circuit_id ?? result.search_query ?? "More detail needed"}</strong>
              <small>{result.provider_label}{result.fault_distance_ft ? ` · ${result.fault_distance_ft.toLocaleString()} ft` : ""}</small>
            </div>
            {result.status === "ready" && result.selected_circuit_id && (
              <button onClick={() => onOpenInvestigation(result)}>Open investigation <ArrowRight size={15} /></button>
            )}
          </div>
        )}

        {intake.isError && <p className="intake-error">{intake.error.message}</p>}

        <form className="intake-composer" onSubmit={submit}>
          <textarea
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                send(draft);
              }
            }}
            maxLength={1200}
            placeholder="Example: High loss on DXR-7001 at 18,420 ft…"
            aria-label="Describe the fiber investigation"
          />
          <button disabled={!draft.trim() || intake.isPending} aria-label="Resolve against network"><Send size={17} /></button>
        </form>

        <div className="quick-prompts">
          <span>Try a known demo</span>
          {quickPrompts.map((prompt) => <button key={prompt} onClick={() => send(prompt)}>{prompt}</button>)}
        </div>
      </div>
    </section>
  );
}

function PipelineNode({
  icon,
  label,
  detail,
  active = false,
}: {
  icon: React.ReactNode;
  label: string;
  detail: string;
  active?: boolean;
}) {
  return <div className={`pipeline-node ${active ? "active" : ""}`}><span>{icon}</span><strong>{label}</strong><small>{detail}</small></div>;
}
