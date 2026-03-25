import { create } from 'zustand';

type FormState = 'idle' | 'email-focused' | 'email-typing' | 'password-focused' | 'password-typing' | 'submit' | 'success' | 'error';

interface LoginStore {
  formState: FormState;
  setFormState: (state: FormState) => void;
}

export const useLoginStore = create<LoginStore>((set) => ({
  formState: 'idle',
  setFormState: (state) => set({ formState: state }),
}));
