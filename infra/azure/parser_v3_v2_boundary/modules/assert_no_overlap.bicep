/*
  Refusal gate for an overlapping address plan.

  Bicep has no "fail with a message" statement, but an @allowed constraint on a
  module parameter is a real, supported, deployment-time refusal. Passing a
  non-zero conflict count here stops the deployment before a single resource is
  created, which is the point: an overlapping boundary must never exist even
  briefly.

  The module is deployed at subscription scope so that it does not depend on
  the boundary resource group having been created first. A gate that only fires
  after something exists is not a gate.

  The constraint is a min/max pair rather than @allowed([0]), and the caller
  passes the count through any(). Both choices are forced by how Bicep types
  constrained parameters, and the reason is worth writing down because it looks
  like evasion and is not.

  @allowed([0]) -- and, it turns out, @minValue(0)/@maxValue(0) as well --
  refines the parameter's *type* to the literal 0. Bicep then rejects any
  argument it cannot statically prove is 0, which includes the correct answer:
  length() of a computed array is typed int, so the gate would fail every
  build, including the ones with no conflict. A gate that refuses everything is
  removed by the first person it inconveniences.

  any() suppresses that static narrowing only. The @minValue/@maxValue pair
  survives into the compiled ARM template and is enforced by ARM during
  preflight, before any resource is created, which is the moment the refusal is
  actually wanted. The compile-time half of the same check lives in
  tests/test_parser_v3_v2_boundary_iac.py, which recomputes the conflict set
  from the committed address plan and fails if it is not empty.
*/

targetScope = 'subscription'

@description('Number of already-allocated prefixes that overlap the boundary VNet. Must be zero.')
@minValue(0)
@maxValue(0)
param conflictingPrefixCount int

output nonOverlapping bool = conflictingPrefixCount == 0
