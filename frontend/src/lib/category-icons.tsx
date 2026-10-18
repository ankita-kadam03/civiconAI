import {
  Building2,
  Droplets,
  Lamp,
  MapPin,
  Signpost,
  Trash2,
  Trees,
  Waves,
  Zap,
  type LucideIcon,
} from "lucide-react";

const ICON_MAP: Record<string, LucideIcon> = {
  road: MapPin,
  "trash-2": Trash2,
  droplets: Droplets,
  waves: Waves,
  lamp: Lamp,
  signpost: Signpost,
  trees: Trees,
  "building-2": Building2,
  "map-pin": MapPin,
  zap: Zap,
};

/** Seed slugs → icon keys from backend categories. */
const SLUG_MAP: Record<string, keyof typeof ICON_MAP> = {
  potholes: "road",
  garbage: "trash-2",
  water: "droplets",
  drainage: "waves",
  streetlights: "lamp",
  "traffic-signs": "signpost",
  parks: "trees",
  infrastructure: "building-2",
  other: "map-pin",
  electrical: "zap",
  flooding: "waves",
};

export function categoryIcon(slugOrIcon?: string | null): LucideIcon {
  if (!slugOrIcon) return MapPin;
  const raw = slugOrIcon.trim().toLowerCase();
  if (ICON_MAP[raw]) return ICON_MAP[raw];
  const viaSlug = SLUG_MAP[raw];
  if (viaSlug && ICON_MAP[viaSlug]) return ICON_MAP[viaSlug];
  return MapPin;
}

export function CategoryIconBadge({
  slugOrIcon,
  className,
  size = 20,
}: {
  slugOrIcon?: string | null;
  className?: string;
  size?: number;
}) {
  const Icon = categoryIcon(slugOrIcon);
  return (
    <span
      className={
        className ||
        "flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-teal/15 text-teal"
      }
    >
      <Icon size={size} aria-hidden />
    </span>
  );
}
