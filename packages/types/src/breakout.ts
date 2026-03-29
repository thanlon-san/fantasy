import { z } from "zod";

export const BreakoutAlertSchema = z.object({
  player: z.string(),
  signal: z.enum(["STRONG", "EMERGING", "WATCH", "FADING"]),
  confidence: z.number(),
  summary: z.string(),
  advice: z.string().optional(),
  improving: z.array(z.string()).optional(),
  declining: z.array(z.string()).optional(),
});

export type BreakoutAlert = z.infer<typeof BreakoutAlertSchema>;

export const PitchMixChangeSchema = z.object({
  change_type: z.string(),
  pitch_type: z.string(),
  pitch_name: z.string(),
  description: z.string(),
  magnitude: z.number(),
  impact: z.enum(["positive", "negative", "neutral"]),
});

export type PitchMixChange = z.infer<typeof PitchMixChangeSchema>;

export const PitchMixEvolutionSchema = z.object({
  pitcher_name: z.string(),
  pitcher_id: z.number(),
  changes: z.array(PitchMixChangeSchema),
  total_changes: z.number(),
  breakout_score: z.number(),
  summary: z.string(),
});

export type PitchMixEvolution = z.infer<typeof PitchMixEvolutionSchema>;

export const RegressionCandidateSchema = z.object({
  name: z.string(),
  player_type: z.string(),
  team: z.string().optional(),
  position: z.string().optional(),
  direction: z.string(),
  ba: z.number().nullable().optional(),
  xba: z.number().nullable().optional(),
  slg: z.number().nullable().optional(),
  xslg: z.number().nullable().optional(),
  xwoba: z.number().nullable().optional(),
  ba_delta: z.number().nullable().optional(),
  era: z.number().nullable().optional(),
  xera: z.number().nullable().optional(),
  fip: z.number().nullable().optional(),
  era_fip_delta: z.number().nullable().optional(),
  confidence: z.number(),
  summary: z.string(),
  improving_metrics: z.array(z.string()),
});

export type RegressionCandidate = z.infer<typeof RegressionCandidateSchema>;
