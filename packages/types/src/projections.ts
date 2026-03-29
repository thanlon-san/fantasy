import { z } from "zod";

export const HitterProjectionSchema = z.object({
  name: z.string(),
  team: z.string(),
  position: z.string(),
  source: z.string(),
  pa: z.number(),
  avg: z.number(),
  hr: z.number(),
  rbi: z.number(),
  sb: z.number(),
  ops: z.number(),
  wrc_plus: z.number(),
  war: z.number(),
  ros_value: z.number(),
});

export type HitterProjection = z.infer<typeof HitterProjectionSchema>;

export const PitcherProjectionSchema = z.object({
  name: z.string(),
  team: z.string(),
  position: z.string(),
  source: z.string(),
  ip: z.number(),
  era: z.number(),
  whip: z.number(),
  k: z.number(),
  qs: z.number(),
  fip: z.number(),
  k_bb_pct: z.number(),
  war: z.number(),
  ros_value: z.number(),
});

export type PitcherProjection = z.infer<typeof PitcherProjectionSchema>;

export const TradeCategoryImpactSchema = z.object({
  stat_id: z.string(),
  name: z.string(),
  label: z.string(),
  group: z.string(),
  better: z.string(),
  before_value: z.number().nullable(),
  after_value: z.number().nullable(),
  delta: z.number().nullable(),
  before_rank: z.number().nullable(),
  after_rank: z.number().nullable(),
  rank_change: z.number().nullable(),
  verdict: z.string(),
});

export type TradeCategoryImpact = z.infer<typeof TradeCategoryImpactSchema>;

export const TradeResultSchema = z.object({
  give_player: z.string(),
  get_player: z.string(),
  give_is_pitcher: z.boolean(),
  get_is_pitcher: z.boolean(),
  give_ros_value: z.number().nullable(),
  get_ros_value: z.number().nullable(),
  categories: z.array(TradeCategoryImpactSchema),
  cats_gained: z.number(),
  cats_lost: z.number(),
  cats_neutral: z.number(),
  net_rank_change: z.number(),
  win_probability_delta: z.number(),
  summary: z.string(),
  generated_at: z.string(),
});

export type TradeResult = z.infer<typeof TradeResultSchema>;
