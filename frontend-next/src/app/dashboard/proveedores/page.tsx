import { auth } from '@clerk/nextjs/server';
import { redirect } from 'next/navigation';
import ProviderConsole from '@/components/ProviderConsole';

export default async function ProviderPage() {
  const { userId } = await auth();
  if (!userId) redirect('/sign-in');
  return <ProviderConsole />;
}
