import type { Routine, RoutineStep, StepInput } from './api/types';
export function routineInputs(steps: RoutineStep[]): StepInput[] {
  return steps.map((step, index) => ({
    step_order: index + 1,
    step_type: step.step_type,
    product_id: step.product.id,
    notes: step.notes,
  }));
}
export function findRoutine(routines: Routine[], slot: string) {
  return routines.find((routine) => routine.slot === slot);
}
