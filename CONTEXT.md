# Intelligent Pick-and-Place Robot

This context describes how a user expresses an arrangement goal and how the system represents, attempts, and reports that goal.

## Language

**User Command Station (UCS)**:
The user-facing part of the system through which a person expresses and follows an arrangement goal.
_Avoid_: Front end, command client

**Stacker Controller (SC)**:
The part of the system responsible for attempting a target arrangement and reporting its outcome.
_Avoid_: Back end, robot planner

**Simulated Stacker Controller**:
A non-physical substitute for the Stacker Controller that reproduces its externally observable behaviour without claiming robot execution or visual verification.
_Avoid_: Fake robot, mock backend

**Arrangement request**:
A user's spoken or typed expression of a desired arrangement.
_Avoid_: Robot instruction, movement plan

**Target arrangement**:
A complete one-to-one assignment of the elephant, bear, and hippo to the three front positions.
_Avoid_: Robot plan, move sequence

**Front position**:
One of the three user-visible destinations: `front_left`, `front_center`, or `front_right`.
_Avoid_: Buffer position, arm pose

**Current draft**:
A proposed target arrangement that has not been confirmed by the user.
_Avoid_: Pending command

**Active command**:
A confirmed target arrangement whose terminal outcome is still unknown.
_Avoid_: Current draft, queued command

**Last successful arrangement**:
The most recent target arrangement reported as successfully completed. It is remembered context, not independently observed physical state.
_Avoid_: Current arrangement, verified arrangement

**Execution result**:
The terminal account of whether the Stacker Controller began and completed its attempt.
_Avoid_: Verification result, placement proof

**Verification result**:
An assessment of the achieved arrangement that is independent of the execution result and may not be performed.
_Avoid_: Execution result, success status
