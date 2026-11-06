"""
Synthetic Clickstream Generator for Checkout A/B Test Simulation.

Generates realistic e-commerce session logs mimicking tracking data (e.g., GA4/Segment)
to benchmark experimentation and funnel analysis workflows.
"""

import os
import random
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

def generate_ab_test_data(
    n_sessions: int = 125_000,
    start_date: str = "2026-10-01",
    days: int = 21,
    random_state: int = 42
) -> pd.DataFrame:
    np.random.seed(random_state)
    random.seed(random_state)
    
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    
    # Generate unique user pool (some returning users have multiple sessions)
    n_users = int(n_sessions * 0.85)
    user_ids = [f"U_{i:06d}" for i in range(1, n_users + 1)]
    assigned_users = np.random.choice(user_ids, size=n_sessions, replace=True)
    
    # True user-level 50:50 assignment
    user_variant_map = {uid: ("treatment" if np.random.rand() < 0.50 else "control") for uid in user_ids}
    
    # Introduce small realistic tracking artifact: 0.4% multi-device / cookie reset conflicts
    conflicted_users = set(random.sample(user_ids, int(n_users * 0.004)))
    
    # Session timestamps across 21 days
    time_offsets_sec = np.random.exponential(scale=3600*24*4, size=n_sessions) % (days * 86400)
    timestamps = [start_dt + timedelta(seconds=float(sec)) for sec in time_offsets_sec]
    timestamps.sort()
    
    # Device mix: ~68% mobile, ~32% desktop
    devices = np.random.choice(["mobile", "desktop"], size=n_sessions, p=[0.68, 0.32])
    # User tier: ~55% new, ~45% returning
    user_tiers = np.random.choice(["new_user", "returning_user"], size=n_sessions, p=[0.55, 0.45])
    
    records = []
    
    for i in range(n_sessions):
        uid = assigned_users[i]
        ts = timestamps[i]
        device = devices[i]
        tier = user_tiers[i]
        
        # Variant assignment with potential tracking conflict
        if uid in conflicted_users and random.random() < 0.3:
            variant = "treatment" if user_variant_map[uid] == "control" else "control"
        else:
            variant = user_variant_map[uid]
        
        # Funnel stage transition probabilities
        if variant == "control":
            p_step2 = 0.68 if device == "desktop" else 0.67
            p_step3 = 0.41 if tier == "returning_user" else 0.38
            p_step4 = 0.40 if device == "desktop" else 0.38
            base_duration = np.random.normal(loc=142, scale=35)
        else:
            # Treatment shows notable UX lift on mobile devices due to responsive 1-page checkout
            p_step2 = 0.73 if device == "mobile" else 0.70
            p_step3 = 0.47 if device == "mobile" else 0.44
            p_step4 = 0.39 if tier == "returning_user" else 0.36
            base_duration = np.random.normal(loc=96, scale=22)
            
        # Determine furthest reached funnel step
        if np.random.rand() < p_step2:
            if np.random.rand() < p_step3:
                if np.random.rand() < p_step4:
                    furthest_step = "4_order_completed"
                    converted = 1
                else:
                    furthest_step = "3_payment_method"
                    converted = 0
            else:
                furthest_step = "2_shipping_address"
                converted = 0
        else:
            furthest_step = "1_view_cart"
            converted = 0
            
        checkout_sec = max(15, int(base_duration * (0.3 if furthest_step == "1_view_cart" else (0.6 if furthest_step == "2_shipping_address" else 1.0))))
        
        if converted == 1:
            # Right-skewed e-commerce order value distribution
            order_val = round(float(np.random.lognormal(mean=3.95, sigma=0.65)), 2)
            payment_error = 1 if np.random.rand() < (0.019 if variant == "treatment" else 0.021) else 0
        else:
            order_val = 0.0
            payment_error = 1 if (furthest_step == "3_payment_method" and np.random.rand() < 0.08) else 0
            
        records.append({
            "session_id": f"S_{i+1:07d}",
            "user_id": uid,
            "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "variant": variant,
            "device": device,
            "user_tier": tier,
            "furthest_funnel_step": furthest_step,
            "converted": converted,
            "order_value_usd": order_val,
            "checkout_duration_sec": checkout_sec,
            "payment_error": payment_error
        })
        
    df = pd.DataFrame(records)
    
    # Inject a few duplicate rows to emulate tracking double-fires
    duplicates = df.sample(n=35, random_state=random_state)
    df = pd.concat([df, duplicates], ignore_index=True)
    df = df.sample(frac=1, random_state=random_state).reset_index(drop=True)
    
    return df

if __name__ == "__main__":
    output_dir = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "ecommerce_ab_test_raw.csv")
    
    print(f"Generating sample e-commerce checkout logs...")
    df = generate_ab_test_data(n_sessions=125_000)
    df.to_csv(output_path, index=False)
    print(f"Done. Saved {len(df):,} records to: {output_path}")
