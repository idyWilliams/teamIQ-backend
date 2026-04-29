# OAuth Integration Error Handling - Summary

### Backend (`app/api/v1/integrations.py`)


```typescript
'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Image, { StaticImageData } from 'next/image';
// ... your imports ...

export default function OAuthCallback({ params }: { params: { provider: string } }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [state, setState] = useState<CallbackState>('success');
  const [errorMessage, setErrorMessage] = useState<string>('');

  const provider = params.provider;
  const config = PROVIDER_CONFIG[provider] || {
    name: provider.charAt(0).toUpperCase() + provider.slice(1),
    icon: '🔗',
    color: 'from-blue-600 to-indigo-600'
  };

  useEffect(() => {
    const success = searchParams.get('success');
    const error = searchParams.get('error');

    if (error === 'true') {
      setState('error');
      setErrorMessage(
        `Failed to connect ${config.name}. This could be due to:\n` +
        `• Invalid credentials\n` +
        `• Redirect URI mismatch\n` +
        `• Network issues\n\n` +
        `Please check your configuration and try again.`
      );
      setTimeout(() => router.push('/organization/settings?tab=integrated-apps'), 5000);
    } else if (success === 'true') {
      setState('success');
      setTimeout(() => {
        router.push('/organization/settings?tab=integrated-apps');
      }, 2000);
    } else {
      setState('error');
      setErrorMessage('Invalid callback state.');
      setTimeout(() => router.push('/organization/settings?tab=integrated-apps'), 3000);
    }
  }, [searchParams, router, config.name]);


}
```


