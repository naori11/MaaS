/** @type {import('@commitlint/types').UserConfig} */
module.exports = {
  extends: ['@commitlint/config-conventional'],
  rules: {
    // Match the canonical types from our convention
    'type-enum': [
      2,
      'always',
      [
        'feat', 'fix', 'docs', 'build', 'refactor',
        'chore', 'ci', 'test', 'revert', 'perf',
      ],
    ],
    // Enforce 72-char subject line
    'header-max-length': [2, 'always', 72],
    // Lowercase subject
    'subject-case': [2, 'never', ['start-case', 'pascal-case', 'upper-case']],
    // No trailing period
    'subject-full-stop': [2, 'never', '.'],
    // Body wrapping (warning, not error)
    'body-max-line-length': [1, 'always', 100],
  },
};
