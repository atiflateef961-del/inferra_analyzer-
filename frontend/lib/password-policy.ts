export const PASSWORD_MIN_LENGTH = 8;

export const PASSWORD_REQUIREMENTS = {
  minLength: PASSWORD_MIN_LENGTH,
  uppercase: /[A-Z]/,
  lowercase: /[a-z]/,
  number: /\d/,
  special: /[^A-Za-z0-9]/,
} as const;

export function validatePassword(password: string): string[] {
  const errors: string[] = [];

  if (password.length < PASSWORD_MIN_LENGTH) {
    errors.push(`Password must be at least ${PASSWORD_MIN_LENGTH} characters long.`);
  }
  if (!PASSWORD_REQUIREMENTS.uppercase.test(password)) {
    errors.push("Password must contain an uppercase letter.");
  }
  if (!PASSWORD_REQUIREMENTS.lowercase.test(password)) {
    errors.push("Password must contain a lowercase letter.");
  }
  if (!PASSWORD_REQUIREMENTS.number.test(password)) {
    errors.push("Password must contain a number.");
  }
  if (!PASSWORD_REQUIREMENTS.special.test(password)) {
    errors.push("Password must contain a special character.");
  }

  return errors;
}
