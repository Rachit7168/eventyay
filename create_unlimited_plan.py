from eventyay_business.models import Tier, TierVersion, TierEntitlement, Subscription, SubscriptionStatus, TierStatus, BillingInterval
from eventyay_business.capabilities import get_all_capabilities, CapabilityValueType
from django.utils.timezone import now
from datetime import timedelta
from django.apps import apps

def main():
    print("Creating Unlimited Plan...")
    tier, created = Tier.objects.get_or_create(
        slug="unlimited",
        defaults={
            "name": "Unlimited Plan",
            "description": "Unlimited everything",
            "status": TierStatus.PUBLISHED,
            "is_public": False,
        }
    )
    if not created and tier.status != TierStatus.PUBLISHED:
        tier.status = TierStatus.PUBLISHED
        tier.save()

    tier_version, created = TierVersion.objects.get_or_create(
        tier=tier,
        version=1,
        defaults={
            "effective_from": now(),
            "published_at": now(),
        }
    )

    print("Adding unlimited entitlements...")
    caps = get_all_capabilities()
    for cap in caps:
        if cap.value_type == CapabilityValueType.BOOLEAN:
            val = "true"
        elif cap.value_type == CapabilityValueType.INTEGER:
            val = "999999999"
        elif cap.value_type in (CapabilityValueType.DECIMAL, CapabilityValueType.MONEY):
            val = "0.0"
        else:
            val = "unlimited"

        TierEntitlement.objects.update_or_create(
            tier_version=tier_version,
            capability=cap.name,
            defaults={
                "value": val,
                "overage_allowed": False
            }
        )

    print("Attaching to all organizers...")
    Organizer = apps.get_model('base', 'Organizer')
    organizers = Organizer.objects.all()
    for org in organizers:
        # Check if they already have an active subscription
        subs = Subscription.objects.filter(organizer=org, status__in=[SubscriptionStatus.ACTIVE, SubscriptionStatus.PENDING])
        for sub in subs:
            sub.status = SubscriptionStatus.CANCELED
            sub.cancel_at = now()
            sub.save()

        # Create new subscription
        Subscription.objects.create(
            organizer=org,
            tier_version=tier_version,
            status=SubscriptionStatus.ACTIVE,
            billing_interval=BillingInterval.ANNUAL,
            starts_at=now(),
            ends_at=now() + timedelta(days=36500) # 100 years
        )
        print(f"Attached Unlimited Plan to organizer {org.slug}")

    print("Done!")

if __name__ == "__main__":
    main()
