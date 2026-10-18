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

const MAP: Record<string, LucideIcon> = {
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

export function categoryIcon(slugOrIcon?: string | null): LucideIcon {
  if (!slugOrIcon) return MapPin;
  return MAP[slugOrIcon] || MapPin;
}
