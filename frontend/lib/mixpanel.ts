import mixpanel from 'mixpanel-browser';

const MIXPANEL_TOKEN = process.env.NEXT_PUBLIC_MIXPANEL_TOKEN || '61b455f4dde35d5c09112cf09c2248b1';

let initialized = false;

export const initMixpanel = () => {
  if (initialized || typeof window === 'undefined') return;

  const apiHost = process.env.NODE_ENV === 'production'
    ? 'https://api.notetubeai.in/mp'
    : 'https://api-js.mixpanel.com';

  mixpanel.init(MIXPANEL_TOKEN, {
    debug: process.env.NODE_ENV !== 'production',
    track_pageview: true,
    persistence: 'localStorage',
    ignore_dnt: true,
    api_host: apiHost,
  });

  initialized = true;
};

export const identifyUser = (userId: string, traits?: Record<string, any>) => {
  if (!initialized || typeof window === 'undefined') return;
  mixpanel.identify(userId);
  if (traits) {
    mixpanel.people.set(traits);
    // Register email/name as super properties so they appear on every event
    const superProps: Record<string, any> = {};
    if (traits.$email) superProps.email = traits.$email;
    if (traits.$name) superProps.name = traits.$name;
    if (Object.keys(superProps).length > 0) {
      mixpanel.register(superProps);
    }
  }
};

export const resetMixpanel = () => {
  if (!initialized || typeof window === 'undefined') return;
  mixpanel.unregister('email');
  mixpanel.unregister('name');
  mixpanel.reset();
};

export const track = (event: string, properties?: Record<string, any>) => {
  if (!initialized || typeof window === 'undefined') return;
  mixpanel.track(event, properties);
};
