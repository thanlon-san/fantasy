import { z } from "zod";

export const TierStatsSchema = z.object({
  total: z.number(),
  correct: z.number(),
  accuracy: z.number(),
});

export type TierStats = z.infer<typeof TierStatsSchema>;

export const LineupAccuracySchema = z.object({
  total: z.number(),
  correct: z.number(),
  accuracy: z.number(),
  by_tier: z.record(z.string(), TierStatsSchema),
});

export type LineupAccuracy = z.infer<typeof LineupAccuracySchema>;

export const BreakoutAccuracySchema = z.object({
  total: z.number(),
  correct: z.number(),
  accuracy: z.number(),
  by_signal: z.record(z.string(), TierStatsSchema),
});

export type BreakoutAccuracy = z.infer<typeof BreakoutAccuracySchema>;

export const BreakoutPredictionRecordSchema = z.object({
  date: z.string(),
  player_name: z.string(),
  player_type: z.string(),
  signal: z.string(),
  confidence: z.number(),
  improving_metrics: z.array(z.string()),
  was_successful: z.boolean().nullable(),
  success_score: z.number().nullable(),
});

export type BreakoutPredictionRecord = z.infer<typeof BreakoutPredictionRecordSchema>;

export const AccuracyReportSchema = z.object({
  lineup: LineupAccuracySchema,
  breakout: BreakoutAccuracySchema,
  recent_breakout_predictions: z.array(BreakoutPredictionRecordSchema),
  waiver_transaction_count: z.number(),
  generated_at: z.string(),
});

export type AccuracyReport = z.infer<typeof AccuracyReportSchema>;
