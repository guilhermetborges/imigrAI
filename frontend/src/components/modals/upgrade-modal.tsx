import { Button } from "@/components/ui/button";

interface UpgradeModalProps {
  isOpen: boolean;
  title?: string;
  description?: string;
  onClose: () => void;
  onUpgrade: () => void;
}

export function UpgradeModal({
  isOpen,
  title = "Upgrade necessario",
  description = "Esse recurso exige plano Pro. Faca upgrade para continuar.",
  onClose,
  onUpgrade
}: Readonly<UpgradeModalProps>): JSX.Element | null {
  if (!isOpen) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 p-4">
      <div className="w-full max-w-md rounded-2xl border border-ink/10 bg-white p-6 shadow-card">
        <h2 className="font-serif text-3xl">{title}</h2>
        <p className="mt-3 text-sm text-muted">{description}</p>
        <div className="mt-6 flex gap-3">
          <Button variant="ghost" onClick={onClose}>
            Agora nao
          </Button>
          <Button onClick={onUpgrade}>Fazer upgrade</Button>
        </div>
      </div>
    </div>
  );
}
