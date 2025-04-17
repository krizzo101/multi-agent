# Git Workflow Guidelines

## Branching Strategy

Our project follows a feature-based branching strategy:

- `main` - Production-ready code
- `develop` - Integration branch for features
- Feature branches - Used for all development work

### Branch Naming Conventions

All feature branches should follow this naming pattern:
```
<type>/<ticket-number>-<short-description>
```

Where `<type>` is one of:
- `feature/` - New features
- `bugfix/` - Bug fixes
- `hotfix/` - Critical fixes for production
- `data-migration/` - Data migration tasks
- `app-services/` - Application services
- `ui/` - User interface components
- `refactor/` - Code refactoring
- `docs/` - Documentation updates

Examples:
- `feature/ABC-123-user-authentication`
- `bugfix/ABC-456-fix-login-validation`
- `data-migration/ABC-789-user-data-schema-update`

## Commit Standards

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

- **Type**: Describes the kind of change
  - `feat`: New feature
  - `fix`: Bug fix
  - `docs`: Documentation changes
  - `style`: Code style/formatting changes
  - `refactor`: Code refactoring with no feature changes
  - `test`: Adding/updating tests
  - `chore`: Build process or tool changes

- **Scope**: The module, component, or area affected
- **Subject**: A concise description of the change (use imperative mood)
- **Body**: Detailed explanation (optional)
- **Footer**: Breaking changes, issue references (optional)

### Examples

```
feat(auth): implement JWT authentication

Add JWT-based authentication with token refresh functionality.

Closes #123
```

```
fix(ui): correct validation error display on login form

Error messages now appear directly below the relevant input field.
```

## Pull Request Process

1. Create a feature branch from `develop`
2. Implement your changes with regular commits
3. Push your branch to the remote repository
4. Open a pull request to merge into `develop`
5. Ensure the PR has:
   - A clear title and description
   - Passing CI/CD checks
   - Required approvals from team members
6. Address review comments
7. Merge using "Squash and merge" option

## Code Review Checklist

- [ ] Code follows project style guidelines
- [ ] Tests are included and passing
- [ ] Documentation is updated
- [ ] No unnecessary dependencies added
- [ ] No debugging/commented code left in
- [ ] Commits follow message conventions
- [ ] Changes address the requirements in the ticket

## Merge and Deployment

1. Feature branches merge into `develop`
2. Release candidates are created from `develop`
3. After testing, release branches merge into `main`
4. All merges to `main` are tagged with a version number
5. Hotfixes may merge directly to `main` (and backported to `develop`)

## Git Hooks

The repository includes git hooks for:

1. Pre-commit: Code linting and formatting
2. Pre-push: Running unit tests
3. Commit-msg: Validating commit message format

Install hooks with: `npm run prepare` 