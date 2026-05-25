export interface RewardState {
  current_stamps: number;
  stamps_for_reward: number;
  stamps_remaining: number;
  reward_ready: boolean;
  progress_percent: number;
}

export function computeRewardState(
  currentStamps: number,
  stampsForReward: number,
): RewardState {
  const stampsRemaining = Math.max(0, stampsForReward - currentStamps);
  const rewardReady = currentStamps >= stampsForReward;
  const progressPercent = Math.min(
    100,
    Math.round((currentStamps / stampsForReward) * 100),
  );
  return {
    current_stamps: currentStamps,
    stamps_for_reward: stampsForReward,
    stamps_remaining: stampsRemaining,
    reward_ready: rewardReady,
    progress_percent: progressPercent,
  };
}
