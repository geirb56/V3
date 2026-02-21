import { useState, useEffect } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
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

const TierCard = ({ tier, isAnnual, currentTier, onSubscribe, subscribing }) => {
  const price = isAnnual ? tier.priceAnnual : tier.priceMonthly;
  const monthlyEquivalent = isAnnual && tier.priceAnnual > 0 ? (tier.priceAnnual / 12).toFixed(2) : null;
  const isCurrentTier = tier.id === currentTier;
  
  return (
    <Card className={`relative overflow-hidden ${tier.highlight ? "border-amber-500 bg-gradient-to-b from-amber-500/5 to-transparent" : "border-border"} ${isCurrentTier ? "ring-2 ring-primary" : ""}`}>
      {tier.badge && (
        <div className="absolute top-0 right-0">
          <Badge className={`rounded-none rounded-bl-lg text-[9px] ${tier.badge === "Populaire" ? "bg-amber-500" : "bg-primary"}`}>
            {tier.badge}
          </Badge>
        </div>
      )}
      
      <CardContent className="p-5">
        <div className="mb-4">
          <h3 className="font-heading text-lg font-bold">{tier.name}</h3>
          <p className="text-xs text-muted-foreground">{tier.description}</p>
        </div>

        <div className="mb-4">
          {tier.priceMonthly === 0 ? (
            <div className="text-3xl font-bold">Gratuit</div>
          ) : (
            <div>
              <div className="flex items-baseline gap-1">
                <span className="text-3xl font-bold">{price}€</span>
                <span className="text-sm text-muted-foreground">/{isAnnual ? "an" : "mois"}</span>
              </div>
              {monthlyEquivalent && (
                <div className="text-xs text-muted-foreground mt-1">
                  <span className="line-through">{tier.priceMonthly}€/mois</span>
                  <span className="text-green-500 ml-2">→ {monthlyEquivalent}€/mois</span>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="flex items-center gap-2 mb-4 p-2 bg-muted/50 rounded">
          <MessageCircle className="w-4 h-4 text-primary" />
          <span className="text-sm font-medium">
            {tier.unlimited ? "Illimité" : `${tier.messagesLimit} msg/mois`}
          </span>
          {tier.unlimited && <span className="text-[9px] text-muted-foreground">*fair-use</span>}
        </div>

        <ul className="space-y-2 mb-6">
          {tier.features.map((feature, idx) => (
            <li key={idx} className="flex items-start gap-2 text-xs">
              <Check className="w-3.5 h-3.5 text-green-500 flex-shrink-0 mt-0.5" />
              <span>{feature}</span>
            </li>
          ))}
        </ul>

        {isCurrentTier ? (
          <Button disabled className="w-full bg-muted text-muted-foreground">
            <Check className="w-4 h-4 mr-2" />
            Plan actuel
          </Button>
        ) : tier.id === "free" ? (
          <Button variant="outline" className="w-full" disabled>
            Inclus
          </Button>
        ) : (
          <Button
            onClick={() => onSubscribe(tier.id)}
            disabled={subscribing === tier.id}
            className={`w-full ${tier.highlight ? "bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600" : ""}`}
          >
            {subscribing === tier.id ? (
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
};

export default function Subscription() {
  const { lang } = useLanguage();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [isAnnual, setIsAnnual] = useState(false);
  const [currentTier, setCurrentTier] = useState("free");
  const [loading, setLoading] = useState(true);
  const [subscribing, setSubscribing] = useState(null);

  const TIERS = [
    {
      id: "free",
      name: "Gratuit",
      description: "Découverte",
      priceMonthly: 0,
      priceAnnual: 0,
      messagesLimit: 10,
      features: ["10 messages coach/mois", "Analyses de séances", "Bilan hebdomadaire", "Sync Strava"],
      highlight: false
    },
    {
      id: "starter",
      name: "Starter",
      description: "Pour débuter",
      priceMonthly: 4.99,
      priceAnnual: 49.99,
      messagesLimit: 25,
      features: ["25 messages coach/mois", "Analyses détaillées", "Coach IA local", "Historique complet"],
      highlight: false
    },
    {
      id: "confort",
      name: "Confort",
      description: "Usage régulier",
      priceMonthly: 5.99,
      priceAnnual: 59.99,
      messagesLimit: 50,
      features: ["50 messages coach/mois", "Toutes les analyses", "Coach IA prioritaire", "Support prioritaire"],
      highlight: true,
      badge: "Populaire"
    },
    {
      id: "pro",
      name: "Pro",
      description: "Illimité",
      priceMonthly: 9.99,
      priceAnnual: 99.99,
      messagesLimit: 150,
      unlimited: true,
      features: ["Messages illimités*", "Accès prioritaire", "Nouvelles fonctionnalités", "Support VIP"],
      highlight: false,
      badge: "Pro"
    }
  ];

  useEffect(() => {
    loadSubscriptionStatus();
    
    const sessionId = searchParams.get("session_id");
    const subscriptionParam = searchParams.get("subscription");
    
    if (sessionId && subscriptionParam === "success") {
      handlePaymentSuccess(sessionId);
    } else if (subscriptionParam === "cancelled") {
      toast.info("Paiement annulé");
      setSearchParams({});
    }
  }, []);

  const loadSubscriptionStatus = async () => {
    try {
      const res = await axios.get(`${API}/subscription/status?user_id=${USER_ID}`);
      setCurrentTier(res.data.tier || "free");
    } catch (error) {
      console.error("Failed to load subscription:", error);
    } finally {
      setLoading(false);
    }
  };

  const handlePaymentSuccess = async (sessionId) => {
    try {
      const res = await axios.get(`${API}/subscription/checkout/status/${sessionId}?user_id=${USER_ID}`);
      if (res.data.status === "completed") {
        toast.success(res.data.message || "Abonnement activé !");
        loadSubscriptionStatus();
      }
    } catch (error) {
      console.error("Payment error:", error);
    }
    setSearchParams({});
  };

  const handleSubscribe = async (tierId) => {
    setSubscribing(tierId);
    try {
      const res = await axios.post(`${API}/subscription/checkout`, {
        origin_url: window.location.origin,
        tier: tierId,
        billing_period: isAnnual ? "annual" : "monthly"
      }, { params: { user_id: USER_ID } });
      
      window.location.href = res.data.checkout_url;
    } catch (error) {
      console.error("Checkout error:", error);
      toast.error("Erreur de paiement");
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
          Choisis le plan qui correspond à ton entraînement
        </p>
      </div>

      <div className="flex items-center justify-center gap-4 mb-8">
        <span className={`text-sm font-medium ${!isAnnual ? "text-foreground" : "text-muted-foreground"}`}>
          Mensuel
        </span>
        <Switch
          checked={isAnnual}
          onCheckedChange={setIsAnnual}
          className="data-[state=checked]:bg-amber-500"
        />
        <span className={`text-sm font-medium ${isAnnual ? "text-foreground" : "text-muted-foreground"}`}>
          Annuel
        </span>
        {isAnnual && (
          <Badge className="bg-green-500 text-white text-[10px]">-17%</Badge>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {TIERS.map((tier) => (
          <TierCard
            key={tier.id}
            tier={tier}
            isAnnual={isAnnual}
            currentTier={currentTier}
            onSubscribe={handleSubscribe}
            subscribing={subscribing}
          />
        ))}
      </div>

      <div className="mt-8 text-center">
        <div className="flex items-center justify-center gap-4 text-xs text-muted-foreground">
          <div className="flex items-center gap-1">
            <Shield className="w-3.5 h-3.5" />
            <span>Paiement sécurisé Stripe</span>
          </div>
        </div>
        <p className="text-[10px] text-muted-foreground mt-2">
          *Fair-use : limite douce de 150 msg/mois pour le plan Pro
        </p>
      </div>
    </div>
  );
}
