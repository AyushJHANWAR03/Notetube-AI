import mixpanel from 'mixpanel-browser';

const MIXPANEL_TOKEN = process.env.NEXT_PUBLIC_MIXPANEL_TOKEN || '61b455f4dde35d5c09112cf09c2248b1';

let initialized = false;

export const initMixpanel = () => {
  if (initialized || typeof window === 'undefined') return;

  mixpanel.init(MIXPANEL_TOKEN, {
    debug: process.env.NODE_ENV !== 'production',
    track_pageview: true,
    persistence: 'localStorage',
    ignore_dnt: true,
  });

  initialized = true;
};

export const identifyUser = (userId: string, traits?: Record<string, any>) => {
  if (!initialized || typeof window === 'undefined') return;
  mixpanel.identify(userId);
  if (traits) {
    mixpanel.people.set(traits);
  }
};

export const resetMixpanel = () => {
  if (!initialized || typeof window === 'undefined') return;
  mixpanel.reset();
};

export const track = (event: string, properties?: Record<string, any>) => {
  if (!initialized || typeof window === 'undefined') return;
  mixpanel.track(event, properties);
};
