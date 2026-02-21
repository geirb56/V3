import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import axios from "axios";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { useLanguage } from "@/context/LanguageContext";
import { Crown, Check, Loader2, MessageCircle, Zap, Shield } from "lucide-react";
import { toast } from "sonner";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const USER_ID = "default";

export default function Subscription() {
  const { lang } = useLanguage();
  const [searchParams, setSearchParams] = useSearchParams();
  const [isAnnual, setIsAnnual] = useState(false);
  const [currentTier, setCurrentTier] = useState("free");
  const [loading, setLoading] = useState(true);
  const [subscribing, setSubscribing] = useState(null);

  const tiers = [
    {
      id: "free",
      name: "Gratuit",
      desc: "Decouverte",
      priceM: 0,
      priceA: 0,
      limit: 10,
      features: ["10 messages coach/mois", "Analyses de seances", "Bilan hebdomadaire"],
      pop: false
    },
    {
      id: "starter",
      name: "Starter",
      desc: "Pour debuter",
      priceM: 4.99,
      priceA: 49.99,
      limit: 25,
      features: ["25 messages coach/mois", "Analyses detaillees", "Coach IA local"],
      pop: false
    },
    {
      id: "confort",
      name: "Confort",
      desc: "Usage regulier",
      priceM: 5.99,
      priceA: 59.99,
      limit: 50,
      features: ["50 messages coach/mois", "Toutes les analyses", "Support prioritaire"],
      pop: true,
      badge: "Populaire"
    },
    {
      id: "pro",
      name: "Pro",
      desc: "Illimite",
      priceM: 9.99,
      priceA: 99.99,
      limit: 150,
      unlimited: true,
      features: ["Messages illimites", "Acces prioritaire", "Support VIP"],
      pop: false,
      badge: "Pro"
    }
  ];

  useEffect(() => {
    loadStatus();
    
    const sessionId = searchParams.get("session_id");
    const subParam = searchParams.get("subscription");
    
    if (sessionId && subParam === "success") {
      handleSuccess(sessionId);
    } else if (subParam === "cancelled") {
      toast.info("Paiement annule");
      setSearchParams({});
    }
  }, []);

  const loadStatus = async () => {
    try {
      const res = await axios.get(API + "/subscription/status?user_id=" + USER_ID);
      setCurrentTier(res.data.tier || "free");
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleSuccess = async (sessionId) => {
    try {
      const res = await axios.get(API + "/subscription/checkout/status/" + sessionId + "?user_id=" + USER_ID);
      if (res.data.status === "completed") {
        toast.success(res.data.message || "Abonnement active!");
        loadStatus();
      }
    } catch (e) {
      console.error(e);
    }
    setSearchParams({});
  };

  const handleSub = async (tierId) => {
    setSubscribing(tierId);
    try {
      const res = await axios.post(API + "/subscription/checkout", {
        origin_url: window.location.origin,
        tier: tierId,
        billing_period: isAnnual ? "annual" : "monthly"
      }, { params: { user_id: USER_ID } });
      
      window.location.href = res.data.checkout_url;
    } catch (e) {
      console.error(e);
      toast.error("Erreur");
      setSubscribing(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="p-4 md:p-6 max-w-6xl mx-auto">
      <div className="text-center mb-8">
        <div className="flex items-center justify-center gap-2 mb-2">
          <Crown className="w-6 h-6 text-amber-500" />
          <h1 className="font-heading text-2xl md:text-3xl uppercase tracking-tight font-bold">
            Abonnements
          </h1>
        </div>
        <p className="text-muted-foreground text-sm">
          Choisis le plan qui correspond a ton entrainement
        </p>
      </div>

      <div className="flex items-center justify-center gap-4 mb-8">
        <span className={!isAnnual ? "text-foreground font-medium text-sm" : "text-muted-foreground text-sm"}>
          Mensuel
        </span>
        <Switch
          checked={isAnnual}
          onCheckedChange={setIsAnnual}
        />
        <span className={isAnnual ? "text-foreground font-medium text-sm" : "text-muted-foreground text-sm"}>
          Annuel
        </span>
        {isAnnual && (
          <Badge className="bg-green-500 text-white text-xs">-17%</Badge>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {tiers.map((t) => {
          const price = isAnnual ? t.priceA : t.priceM;
          const isCurrent = t.id === currentTier;
          
          return (
            <Card key={t.id} className={t.pop ? "border-amber-500" : ""}>
              {t.badge && (
                <div className="absolute top-0 right-0">
                  <Badge className="rounded-none rounded-bl text-xs bg-amber-500">{t.badge}</Badge>
                </div>
              )}
              
              <CardContent className="p-5 relative">
                <div className="mb-4">
                  <h3 className="font-bold text-lg">{t.name}</h3>
                  <p className="text-xs text-muted-foreground">{t.desc}</p>
                </div>

                <div className="mb-4">
                  {t.priceM === 0 ? (
                    <div className="text-2xl font-bold">Gratuit</div>
                  ) : (
                    <div className="flex items-baseline gap-1">
                      <span className="text-2xl font-bold">{price}EUR</span>
                      <span className="text-xs text-muted-foreground">/{isAnnual ? "an" : "mois"}</span>
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-2 mb-4 p-2 bg-muted/50 rounded">
                  <MessageCircle className="w-4 h-4 text-primary" />
                  <span className="text-sm">{t.unlimited ? "Illimite" : t.limit + " msg/mois"}</span>
                </div>

                <ul className="space-y-2 mb-6">
                  {t.features.map((f, i) => (
                    <li key={i} className="flex items-start gap-2 text-xs">
                      <Check className="w-3 h-3 text-green-500 mt-0.5" />
                      <span>{f}</span>
                    </li>
                  ))}
                </ul>

                {isCurrent ? (
                  <Button disabled className="w-full">Plan actuel</Button>
                ) : t.id === "free" ? (
                  <Button variant="outline" className="w-full" disabled>Inclus</Button>
                ) : (
                  <Button
                    onClick={() => handleSub(t.id)}
                    disabled={subscribing === t.id}
                    className="w-full"
                  >
                    {subscribing === t.id ? (
                      <Loader2 className="w-4 h-4 animate-spin mr-2" />
                    ) : (
                      <Zap className="w-4 h-4 mr-2" />
                    )}
                    Choisir
                  </Button>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      <div className="mt-8 text-center text-xs text-muted-foreground">
        <Shield className="w-4 h-4 inline mr-1" />
        Paiement securise Stripe
      </div>
    </div>
  );
}
