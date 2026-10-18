import { z } from "zod";

export const signupSchema = z.object({
  display_name: z.string().min(2, "Please add your name").max(80),
  email: z.string().email("Enter a valid email"),
  password: z.string().min(8, "Use at least 8 characters").max(72),
  phone: z.string().min(8, "Add a mobile number officers can reach").max(20),
  locality: z.string().max(120).optional(),
});

export const loginSchema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(1, "Password is required"),
});

export const reportSchema = z.object({
  title: z.string().min(6, "Add a short title").max(140),
  description: z.string().min(12, "Please describe what you saw").max(4000),
  category_id: z.string().min(1, "Choose a category"),
  locality: z.string().min(2, "Add a locality").max(160),
  address: z.string().max(240).optional(),
  latitude: z.number().min(-90).max(90).optional(),
  longitude: z.number().min(-180).max(180).optional(),
  occurred_at: z.string().optional(),
  is_public: z.boolean().default(true),
});

export type ReportValues = z.infer<typeof reportSchema>;
