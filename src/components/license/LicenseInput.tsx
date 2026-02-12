import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { KeyRound, Mail, Loader2 } from "lucide-react";

interface LicenseInputProps {
  onActivate: (key: string, email: string) => Promise<any>;
  error?: string | null;
}

export function LicenseInput({ onActivate, error }: LicenseInputProps) {
  const [key, setKey] = useState("");
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    if (!key.trim()) { setLocalError("License key is required"); return; }
    if (!email.trim()) { setLocalError("Email is required"); return; }
    setLoading(true);
    try { await onActivate(key.trim(), email.trim()); }
    catch (err) { setLocalError(String(err)); }
    finally { setLoading(false); }
  };

  const handleKeyChange = (value: string) => {
    const cleaned = value.replace(/[^a-zA-Z0-9]/g, "").toUpperCase();
    const parts = cleaned.match(/.{1,4}/g) || [];
    setKey(parts.join("-").slice(0, 19));
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div className="space-y-1.5">
        <label className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
          <KeyRound className="h-3 w-3" /> License Key
        </label>
        <Input placeholder="XXXX-XXXX-XXXX-XXXX" value={key} onChange={(e) => handleKeyChange(e.target.value)} className="font-mono text-center tracking-widest" maxLength={19} />
      </div>
      <div className="space-y-1.5">
        <label className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
          <Mail className="h-3 w-3" /> Email
        </label>
        <Input type="email" placeholder="your@email.com" value={email} onChange={(e) => setEmail(e.target.value)} />
      </div>
      {(error || localError) && (
        <p className="text-xs text-red-500 bg-red-500/10 rounded-md p-2.5 border border-red-500/20">{localError || error}</p>
      )}
      <Button type="submit" className="w-full" size="lg" disabled={loading}>
        {loading ? <><Loader2 className="h-4 w-4 animate-spin" /> Activating...</> : "Activate License"}
      </Button>
    </form>
  );
}
