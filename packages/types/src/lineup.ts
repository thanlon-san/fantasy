import { z } from "zod";
import { PlayerSchema, NotPlayingPlayerSchema } from "./player";

export const DailyLineupSchema = z.object({
  generated_at: z.string().optional(),
  date: z.string().optional(),
  must_start: z.array(PlayerSchema),
  start: z.array(PlayerSchema),
  flex: z.array(PlayerSchema),
  bench: z.array(PlayerSchema),
  not_playing: z.array(NotPlayingPlayerSchema),
  summary: z
    .object({
      total_roster: z.number(),
      playing_today: z.number(),
      not_playing: z.number(),
      must_start_count: z.number().optional(),
      start_count: z.number().optional(),
      flex_count: z.number().optional(),
      bench_count: z.number().optional(),
    })
    .optional(),
});

export type DailyLineup = z.infer<typeof DailyLineupSchema>;

export const SwingCategorySchema = z.object({
  stat_name: z.string(),
  stat_id: z.string(),
  status: z.enum(["close_win", "close_loss"]),
  my_value: z.number().nullable(),
  opp_value: z.number().nullable(),
  focus_players: z.array(z.string()),
  waiver_suggestion: z.string().nullable(),
});

export type SwingCategory = z.infer<typeof SwingCategorySchema>;

export const LineupFocusSchema = z.object({
  week: z.number(),
  swing_categories: z.array(SwingCategorySchema),
  season_started: z.boolean(),
});

export type LineupFocus = z.infer<typeof LineupFocusSchema>;
