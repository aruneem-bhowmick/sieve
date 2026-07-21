export type InterventionType = "INT-01" | "INT-02" | "INT-03";

export interface ReplayEntry {
  task_id: string;
  intervention_type: InterventionType;
  patch_divergence: number;
  outcome_stability: boolean;
  faithfulness_score: number;
  test_result: { passed: string[]; failed: string[] };
  intervention: {
    type: InterventionType | null;
    target_step_id: string | null;
    target_field: "claim" | "constraint" | "hypothesis" | null;
    original_value: string | null;
    replacement_value: string | null;
  };
  final_diff: string;
}

import type { DemoTask } from "../../shared/live_suite";

export type { DemoTask } from "../../shared/live_suite";

export interface ReplayBundle {
  version: number;
  tasks: DemoTask[];
  entries: ReplayEntry[];
  counts: Record<string, number>;
}
