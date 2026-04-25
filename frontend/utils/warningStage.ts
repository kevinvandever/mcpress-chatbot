export type WarningStage = 'silent' | 'soft' | 'stronger' | 'upgrade' | 'hardGate'

export function getWarningStage(questionsUsed: number, questionsLimit: number): WarningStage {
  if (questionsUsed > questionsLimit) return 'hardGate'
  if (questionsUsed === questionsLimit) return 'upgrade'
  if (questionsUsed === questionsLimit - 1) return 'stronger'
  if (questionsUsed === questionsLimit - 2) return 'soft'
  return 'silent'
}
