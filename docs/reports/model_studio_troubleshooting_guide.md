# Model Studio Troubleshooting Guide

## If A Dataset Will Not Preview Or Build

- check whether the selected dataset or source family is `Launchable now`
- confirm the blocker text is specific rather than generic
- if the surface is `Review pending`, do not expect it to build in the routine beta lane

## If A Run Will Not Launch

- confirm a dataset build exists for the current draft
- confirm the selected model family is active in the current lane
- confirm representation and preprocessing choices are compatible with the selected dataset scope

## If Analysis Or Compare Looks Wrong

- check requested versus resolved backend and hardware
- confirm the selected lane is still within the current beta truth boundary
- report the issue with the selected pool, model family, and run id

## If A Blocked Feature Is Unclear

- open the blocked-feature explanation
- check whether the lane is `Review pending` or `Inactive`
- use `Need help / report issue` if the remediation path still feels unclear
