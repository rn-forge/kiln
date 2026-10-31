# review

**Historical record:** proposals and numbered decisions below describe the
review at that time, not current policy. ADR references use current
destinations; retired references use topic names. Current scope and decisions
are in [the spec board](../../specs/index.md) and
[the decision log](../../adr/index.md).

Phase C from the standardization plan (retired; see [context](../context.md))
was implemented and codex has provided review comments at
'docs/plans/reviews/phase-c-codex.md'

## archetypes

There are a few comments about links and dependencies on the repos. Here are my
thoughts for us to discuss and detemine how to the archetypes should be
designed, defined and used. It is ok reverse/update ADRs or decisions inside the
plan, if the understanding materially changes them. It is ok for you to counter
my feedback based on best practices and proven industry standards.

### python-lib

- There will be repos that publish python libraries for others to use. These
  will be of type monorepo, similar to pykit, and could publish more than one
  package for external consumption.
- The initial scaffold will be similar to what the golden copy looks like today,
  with the root pyproject having minimal depdendencies. it will have the
  standard docs, cicd, tasks et.
- kiln could provide a generator for new lib. take standard arguments like name,
  import path, description etc. and scaffold the new package inside the repo
- this new package will depend on rn-forge-commons for all standard utilities
  and boilerplate abstraction

### python-cli

- There will be standalone apps in python the do not have a web ui. these could
  interactive command line tools or background batches
- both will need the typer, cli, console capabilities currently in
  rn-forge-tooling, along with commons
- mostly ml apps or business batches will fall into this category. they might
  need ability to read/write from and to databases/files etc.
- they will communicate with other resources like azure, for which they can
  consume more packages published by pykit, or declare packages inside the
  repo itself (monorepo) for internal structuring and usage
- now these apps will not need install, update, home directory, doctor, states,
  plugins etc. as capabilities. they will be simple apps that expose a cli
  interface to do functional job which either a user or scheduler invokes
- these capabilities will be needed by a specific class of apps, which are
  installable tools. and will need the capabilities in rn-forge-tooling that
  may not be required by the other type of apps

### python-web

- these comments are common to both django and fastapi based implementations
- webapps will be broadly of 2 types - microservices (no UI) or full app (with
  UI)
- backend implemenation could be django (if batteries included approach is
  needed), or fastapi for leaner implementation. maybe a 'python-web-api'
  archetype with config flag to choose implementation framework
- kiln should also provide generators to create standard structures like models,
  api, serializer etc. to build web apps fast
- even without a formal UI, there might be a need to ship a thin self-contained
  UI layer in these apps, for admin/management operations. think django admin,
  springboot actuator etc.
- then there are full apps that have a full UI app too. this is the monorepo
  pattern with api/ and web/ packages, like apollo and intellibench. maybe a
  'python-web-app' archetype with config flags to choose both backend and
  frontend implementation frameworks
- both kind of archetypes are monorepos with multiple packages, and option to
  add private libraries for structure and management

### ui-lib

- these carry the same principle as python-lib, and will be modeled as monorepos
  publishing multiple libraries for use in other apps. see ngkit.
- these also can provide generators for standard boilerplate code to use the
  library wrappers itself.

### node-web-app

- These are standalone UI apps that consume multiple backend APIs and function
  as a standalone deployments
- These can consume libries published by 'ngkit', or external libraries, or
  create their own internal ones is true nx monorepo pattern
- config flag can drive the type as angular, react or svelte. focus on angular
  for now
