import { z } from "zod";

export const PlayerSchema = z.object({
  player: z.string(),
  position: z.string(),
  team: z.string(),
  opponent: z.string(),
  opponent_pitcher: z.string().optional(),
  game_time: z.string().optional(),
  confidence: z.number(),
  matchup: z.number(),
  parkFactor: z.number(),
  platoon: z.number(),
  form: z.number(),
  breakout: z.number(),
  vegas_total: z.number().nullable().optional(),
  reasons: z.array(z.string()),
  injury: z.string().nullable().optional(),
});

export type Player = z.infer<typeof PlayerSchema>;

export const NotPlayingPlayerSchema = z.object({
  player: z.string(),
  position: z.string(),
  team: z.string(),
  adp: z.number().nullable().optional(),
});

export type NotPlayingPlayer = z.infer<typeof NotPlayingPlayerSchema>;

export const PlayerProfileSchema = z.object({
  name: z.string(),
  found: z.boolean(),
  team: z.string().optional(),
  position: z.string().optional(),
  projection: z
    .object({
      type: z.enum(["hitter", "pitcher"]),
      pa: z.number().optional(),
      avg: z.number().optional(),
      hr: z.number().optional(),
      rbi: z.number().optional(),
      sb: z.number().optional(),
      ops: z.number().optional(),
      wrc_plus: z.number().optional(),
      war: z.number().optional(),
      ros_value: z.number().optional(),
      ip: z.number().optional(),
      era: z.number().optional(),
      whip: z.number().optional(),
      k: z.number().optional(),
      qs: z.number().optional(),
      fip: z.number().optional(),
      k_bb_pct: z.number().optional(),
    })
    .optional(),
  regression: z
    .object({
      direction: z.string(),
      confidence: z.number(),
      summary: z.string(),
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
      improving_metrics: z.array(z.string()),
    })
    .optional(),
  injury: z
    .object({
      badge: z.string(),
      description: z.string(),
      date: z.string().optional(),
    })
    .optional(),
  recent_stats: z.record(z.string(), z.record(z.string(), z.number().nullable())).optional(),
  savant_percentiles: z.record(z.string(), z.number().nullable()).optional(),
  generated_at: z.string().optional(),
});

export type PlayerProfile = z.infer<typeof PlayerProfileSchema>;
