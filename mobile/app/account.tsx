import { useState } from 'react';
import { View } from 'react-native';
import { Button, Input, TextField, Label, FieldError } from 'heroui-native';
import { useMutation } from '@tanstack/react-query';
import { router } from 'expo-router';
import * as Haptics from 'expo-haptics';
import { Screen } from '@/components/Screen';
import { AppText } from '@/components/AppText';
import { LoadingState } from '@/components/DataState';
import { useSession } from '@/lib/session';
import { signIn, errorMessage } from '@/lib/api/client';
import { notifySuccess } from '@/lib/api/queries';
import { colors } from '@/lib/theme';
export default function AccountScreen() {
  const session = useSession((state) => state.session);
  const ready = useSession((state) => state.ready);
  const storageError = useSession((state) => state.storageError);
  const [register, setRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const mutation = useMutation({
    mutationFn: async () => {
      if (!email.trim() || !password) throw new Error('Enter your email and password.');
      if (
        register &&
        (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email.trim()) || !name.trim() || password.length < 8)
      )
        throw new Error('Enter a valid email, your name and a password of at least 8 characters.');
      await signIn(email, password, register ? name : undefined);
    },
    onSuccess: () => {
      setPassword('');
      notifySuccess();
    },
  });
  const signOut = useMutation({
    mutationFn: async () => {
      await useSession.getState().setSession(null);
    },
    onSuccess: notifySuccess,
  });
  return (
    <Screen title="Account">
      {!ready ? (
        <LoadingState />
      ) : session ? (
        <>
          <AppText weight="semibold" style={{ fontSize: 28 }}>
            {session.user.display_name || 'Your account'}
          </AppText>
          <AppText style={{ color: colors.muted }}>{session.user.email}</AppText>
          <Button variant="secondary" onPress={() => router.push('/profile')}>
            <Button.Label>Skin profile</Button.Label>
          </Button>
          <Button variant="secondary" onPress={() => router.push('/routines')}>
            <Button.Label>Your routines</Button.Label>
          </Button>
          <Button variant="secondary" onPress={() => router.push('/recommendations')}>
            <Button.Label>Recommendations</Button.Label>
          </Button>
          <Button
            variant="tertiary"
            isDisabled={signOut.isPending}
            onPress={() => signOut.mutate()}
          >
            <Button.Label>
              {signOut.isPending ? 'Signing out…' : 'Sign out on this device'}
            </Button.Label>
          </Button>
          {signOut.isError && <FieldError>{errorMessage(signOut.error)}</FieldError>}
        </>
      ) : (
        <>
          <AppText weight="semibold" style={{ fontSize: 28 }}>
            {register ? 'Make it personal.' : 'Welcome back.'}
          </AppText>
          {storageError && <FieldError>{storageError}</FieldError>}
          <View style={{ gap: 18 }}>
            {register && (
              <TextField>
                <Label>Your name</Label>
                <Input
                  value={name}
                  onChangeText={setName}
                  maxLength={100}
                  textContentType="name"
                  autoComplete="name"
                  accessibilityLabel="Your name"
                />
              </TextField>
            )}
            <TextField>
              <Label>Email</Label>
              <Input
                value={email}
                onChangeText={setEmail}
                maxLength={255}
                autoCapitalize="none"
                autoCorrect={false}
                keyboardType="email-address"
                textContentType="emailAddress"
                autoComplete="email"
                accessibilityLabel="Email"
              />
            </TextField>
            <TextField>
              <Label>Password</Label>
              <Input
                value={password}
                onChangeText={setPassword}
                maxLength={128}
                secureTextEntry
                textContentType={register ? 'newPassword' : 'password'}
                autoComplete={register ? 'new-password' : 'current-password'}
                accessibilityLabel="Password"
                onSubmitEditing={() => {
                  if (!mutation.isPending) mutation.mutate();
                }}
              />
            </TextField>
            {mutation.isError && <FieldError>{errorMessage(mutation.error)}</FieldError>}
            <Button isDisabled={mutation.isPending} onPress={() => mutation.mutate()}>
              <Button.Label>
                {mutation.isPending ? 'Please wait…' : register ? 'Create account' : 'Sign in'}
              </Button.Label>
            </Button>
            <Button
              variant="tertiary"
              onPress={() => {
                setRegister(!register);
                mutation.reset();
                void Haptics.selectionAsync();
              }}
            >
              <Button.Label>
                {register ? 'I already have an account' : 'Create an account'}
              </Button.Label>
            </Button>
          </View>
        </>
      )}
    </Screen>
  );
}
