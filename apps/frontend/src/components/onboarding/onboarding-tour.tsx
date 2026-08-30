"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import type { CurrentUser } from "@/schemas/auth";

interface TourStep {
  eyebrow: string;
  title: string;
  body: string;
  linkLabel?: string;
  href?: string;
}

function stepsFor(user: CurrentUser): TourStep[] {
  const designer = user.role === "DESIGNER";
  return [
    {
      eyebrow: "Welcome",
      title: "EV Factory Digital Twin",
      body: "Observe AMR battery logistics, test factory changes safely, and keep every production change under human approval.",
    },
    {
      eyebrow: "Your role",
      title: designer ? "Designer" : "Monitor",
      body: designer
        ? "Create immutable layouts, run SimPy candidates, compare KPIs, and submit evidence for independent review."
        : "Review submitted candidates, request specific revisions, and approve or apply only the changes supported by evidence.",
      linkLabel: designer ? "Open layout editor" : "Open review queue",
      href: designer ? "/layouts" : "/scenarios?queue=awaiting",
    },
    {
      eyebrow: "The cockpit",
      title: "Live operations at a glance",
      body: "Overview combines the live factory map with KPI, fleet, and alert tools. The connection banner warns when telemetry may be stale.",
      linkLabel: "Open Overview",
      href: "/",
    },
    {
      eyebrow: "Your first task",
      title: designer ? "Build a candidate" : "Review the queue",
      body: designer
        ? "Start in Layouts, run the result in Scenarios, then follow the Next Action guidance until the candidate is submitted."
        : "Open the awaiting-review queue, compare the candidate with live state, then approve it or request an actionable revision.",
      linkLabel: designer ? "Start in Layouts" : "Review candidates",
      href: designer ? "/layouts" : "/scenarios?queue=awaiting",
    },
  ];
}

export function OnboardingTour({ user }: { user: CurrentUser }) {
  const storageKey = `ft-onboarding-done:${user.id}`;
  const [visible, setVisible] = useState(false);
  const [stepIndex, setStepIndex] = useState(0);
  const [dontShowAgain, setDontShowAgain] = useState(true);
  const persistRef = useRef(dontShowAgain);
  const dialogRef = useRef<HTMLDivElement>(null);
  const titleRef = useRef<HTMLHeadingElement>(null);
  persistRef.current = dontShowAgain;

  useEffect(() => {
    setStepIndex(0);
    setDontShowAgain(true);
    try {
      setVisible(localStorage.getItem(storageKey) !== "1");
    } catch {
      setVisible(true);
    }
  }, [storageKey]);

  const dismiss = useCallback(() => {
    if (persistRef.current) {
      try {
        localStorage.setItem(storageKey, "1");
      } catch {
        // Storage may be unavailable in privacy-restricted browsers; closing still works.
      }
    }
    setVisible(false);
  }, [storageKey]);

  useEffect(() => {
    if (!visible) return;
    const previousFocus = document.activeElement as HTMLElement | null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    titleRef.current?.focus();

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        dismiss();
        return;
      }
      if (event.key !== "Tab") return;
      const focusable = Array.from(dialogRef.current?.querySelectorAll<HTMLElement>(
        'a[href],button:not([disabled]),input:not([disabled])',
      ) ?? []);
      if (focusable.length === 0) return;
      const currentIndex = focusable.indexOf(document.activeElement as HTMLElement);
      if (event.shiftKey && currentIndex <= 0) {
        event.preventDefault();
        focusable.at(-1)?.focus();
      } else if (!event.shiftKey && (currentIndex === -1 || currentIndex === focusable.length - 1)) {
        event.preventDefault();
        focusable[0]?.focus();
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = previousOverflow;
      previousFocus?.focus();
    };
  }, [dismiss, visible]);

  if (!visible) return null;
  const steps = stepsFor(user);
  const step = steps[stepIndex];
  const lastStep = stepIndex === steps.length - 1;

  return (
    <div className="onboarding-overlay">
      <section
        className="onboarding-dialog"
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="onboarding-title"
        aria-describedby="onboarding-description"
      >
        <div className="onboarding-progress" aria-label={`Step ${stepIndex + 1} of ${steps.length}`}>
          {steps.map((_, index) => <i key={index} className={index <= stepIndex ? "active" : ""}/>) }
        </div>
        <span className="eyebrow">{step.eyebrow} · Step {stepIndex + 1} of {steps.length}</span>
        <h2 id="onboarding-title" ref={titleRef} tabIndex={-1}>{step.title}</h2>
        <p id="onboarding-description">{step.body}</p>
        {step.href && step.linkLabel && (
          <Link className="onboarding-link" href={step.href} onClick={dismiss}>{step.linkLabel} →</Link>
        )}
        <label className="onboarding-preference">
          <input
            type="checkbox"
            checked={dontShowAgain}
            onChange={(event) => setDontShowAgain(event.target.checked)}
          />
          Don&apos;t show this tour again
        </label>
        <div className="onboarding-actions">
          <button className="button" type="button" onClick={dismiss}>Skip tour</button>
          <div>
            {stepIndex > 0 && (
              <button className="button" type="button" onClick={() => setStepIndex((value) => value - 1)}>
                Back
              </button>
            )}
            <button
              className="button primary"
              type="button"
              onClick={() => lastStep ? dismiss() : setStepIndex((value) => value + 1)}
            >
              {lastStep ? "Get started" : "Next"}
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
