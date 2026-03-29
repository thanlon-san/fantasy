import { z } from "zod";

const StatWindowSchema = z.object({
  avg: z.number().optional(),
  hr: z.number().optional(),
  rbi: z.number().optional(),
  sb: z.number().optional(),
  obp: z.number().optional(),
  slg: z.number().optional(),
  ops: z.number().optional(),
  bb: z.number().optional(),
  r: z.number().optional(),
  era: z.number().optional(),
  whip: z.number().optional(),
  k: z.number().optional(),
  w: z.number().optional(),
  sv: z.number().optional(),
  qs: z.number().optional(),
  ip: z.number().optional(),
  holds: z.number().optional(),
  games: z.number().optional(),
});

export const WaiverTargetSchema = z.object({
  player: z.string(),
  position: z.string(),
  team: z.string(),
  confidence: z.string(),
  reason: z.string(),
  drop_player: z.string(),
  drop_player_position: z.string(),
  adp: z.number().optional(),
  value_gain: z.number().optional(),
  drop_player_adp: z.number().optional(),
  keeper_cost: z.number().optional(),
  rostered_pct: z.number().optional(),
  trending: z.enum(["HOT", "COLD", "STABLE"]).optional(),
  last_7_days: StatWindowSchema.optional(),
  last_14_days: StatWindowSchema.optional(),
  last_30_days: StatWindowSchema.optional(),
  statcast_changes: z
    .object({
      exit_velo: z.string().optional(),
      hard_hit_pct: z.string().optional(),
      barrel_rate: z.string().optional(),
      velo: z.string().optional(),
      chase_rate: z.string().optional(),
      whiff_rate: z.string().optional(),
    })
    .optional(),
  role_change: z.string().optional(),
  upcoming_schedule: z.string().optional(),
});

export type WaiverTarget = z.infer<typeof WaiverTargetSchema>;
