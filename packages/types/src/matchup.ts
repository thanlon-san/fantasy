import { z } from "zod";

export const MatchupCategorySchema = z.object({
  stat_id: z.string(),
  name: z.string(),
  label: z.string(),
  group: z.enum(["batting", "pitching"]),
  better: z.enum(["high", "low"]),
  my_value: z.number().nullable(),
  opp_value: z.number().nullable(),
  status: z.string(),
  projected_my: z.number().nullable().optional(),
  projected_opp: z.number().nullable().optional(),
  gap_to_flip: z.number().nullable().optional(),
  daily_pace_my: z.number().nullable().optional(),
  recommendation: z.string().nullable().optional(),
});

export type MatchupCategory = z.infer<typeof MatchupCategorySchema>;

export const MatchupSchema = z.object({
  week: z.number(),
  week_start: z.string().nullable(),
  week_end: z.string().nullable(),
  status: z.string(),
  my_team: z.string().nullable(),
  opp_team: z.string().nullable(),
  categories: z.array(MatchupCategorySchema),
  enhanced: z.boolean().optional(),
  days_elapsed: z.number().optional(),
  days_left: z.number().optional(),
  total_days: z.number().optional(),
});

export type Matchup = z.infer<typeof MatchupSchema>;

export const BullpenAlertSchema = z.object({
  closer: z.string(),
  closer_team: z.string(),
  fatigue_score: z.number(),
  fatigue_level: z.enum(["HIGH", "MODERATE", "LOW", "FRESH"]),
  consecutive_days: z.number(),
  pitches_last_3_days: z.number(),
  vulture_candidate: z.string(),
  reason: z.string(),
  committee: z.boolean(),
});

export type BullpenAlert = z.infer<typeof BullpenAlertSchema>;
