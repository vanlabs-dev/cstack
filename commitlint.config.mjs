// Reject the em dash character (U+2014) anywhere in commit messages.
// Built at runtime from its code point so this source file stays ASCII-only.
const EM_DASH = String.fromCharCode(0x2014);

const noEmDashPlugin = {
  rules: {
    'no-em-dash': (parsed) => {
      const raw = parsed.raw ?? '';
      if (raw.includes(EM_DASH)) {
        return [false, 'commit message must not contain em dashes (U+2014)'];
      }
      return [true, ''];
    },
  },
};

export default {
  extends: ['@commitlint/config-conventional'],
  plugins: [noEmDashPlugin],
  rules: {
    'subject-case': [2, 'always', 'lower-case'],
    'subject-full-stop': [2, 'never', '.'],
    'body-max-line-length': [2, 'always', 100],
    'no-em-dash': [2, 'always'],
  },
};
