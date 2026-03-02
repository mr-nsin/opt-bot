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
    if (!isValidKeyFormat(key.trim())) {
      setLocalError("License key must be XXXX-XXXX-XXXX-XXXX (16 letters/numbers from vendor)");
      return;
    }
    setLoading(true);
    try { await onActivate(key.trim(), email.trim()); }
    catch (err) { setLocalError(String(err)); }
    finally { setLoading(false); }
  };

  const handleKeyChange = (value: string) => {
    // If pasting generator output (e.g. "License key:      ABCD-1234-EFGH-5678"), extract the key
    const keyMatch = value.match(/([A-Za-z0-9]{4}-[A-Za-z0-9]{4}-[A-Za-z0-9]{4}-[A-Za-z0-9]{4})/);
    const toClean = keyMatch ? keyMatch[1] : value;
    // Extract only alphanumeric, uppercase, limit to 16 chars (matches license-generator format)
    const cleaned = toClean.replace(/[^a-zA-Z0-9]/g, "").toUpperCase().slice(0, 16);
    const parts = cleaned.match(/.{1,4}/g) || [];
    setKey(parts.join("-"));
  };

  const isValidKeyFormat = (k: string) => {
    const parts = k.split("-");
    return parts.length === 4 && parts.every((p) => p.length === 4 && /^[A-Z0-9]+$/.test(p));
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div className="space-y-1.5">
        <label className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
          <KeyRound className="h-3 w-3" /> License Key
        </label>
        <Input placeholder="XXXX-XXXX-XXXX-XXXX" value={key} onChange={(e) => handleKeyChange(e.target.value)} className="font-mono text-center tracking-widest" maxLength={19} title="Paste the key from your vendor (e.g. A1B2-C3D4-E5F6-G7H8)" />
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
