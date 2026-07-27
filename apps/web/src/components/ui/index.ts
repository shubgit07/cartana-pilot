// Public surface for design-system primitives. Everything else in
// `/components/ui/*` is internal and should not be imported directly by
// consumers — import from this barrel.

export { Badge, badgeVariants } from "./badge";
export type { BadgeProps } from "./badge";
export { Button, buttonVariants } from "./button";
export type { ButtonProps } from "./button";
export {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "./card";
export {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogOverlay,
  DialogPortal,
  DialogTitle,
  DialogTrigger,
} from "./dialog";
export { Input } from "./input";
export type { InputProps } from "./input";
export { Label } from "./label";
export {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectScrollDownButton,
  SelectScrollUpButton,
  SelectSeparator,
  SelectTrigger,
  SelectValue,
} from "./select";
export { Skeleton } from "./skeleton";
export { Tabs, TabsContent, TabsList, TabsTrigger } from "./tabs";
export { Textarea } from "./textarea";
export type { TextareaProps } from "./textarea";
export { ToastProvider, useToast } from "./toast";
export type { ToastInput, ToastVariant } from "./toast";
