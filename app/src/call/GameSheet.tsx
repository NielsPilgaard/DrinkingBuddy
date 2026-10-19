import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { colors } from '../theme';
import { CallSheet } from './CallSheet';
import type { GamePrompt, GameType } from './signaling';

const GAMES: Record<GameType, { label: string; icon: string; blurb: string }> = {
  trivia: { label: 'Trivia', icon: '🧠', blurb: 'Multiple choice, answer together' },
  would_you_rather: { label: 'Would You Rather', icon: '🤔', blurb: 'Two options, pick one' },
  never_have_i_ever: { label: 'Never Have I Ever', icon: '🙈', blurb: 'Confess or take a sip' },
};

type GameSheetProps = {
  gameInvite: { gameType: GameType; fromSelf: boolean } | null;
  activeGame: { gameType: GameType; prompt: GamePrompt; revealed: boolean } | null;
  onStartGame: (gameType: GameType) => void;
  onAcceptGame: () => void;
  onDeclineGame: () => void;
  onNextPrompt: () => void;
  onRevealPrompt: () => void;
  onCloseGame: () => void;
  onClose: () => void;
};

const OPENTDB_ATTRIBUTION =
  'Trivia questions courtesy of Open Trivia DB (opentdb.com), CC BY-SA 4.0.';

/**
 * Sheet for the "play game" call action (tasks/completed/mini-games.md). Renders
 * one of three states: game picker (idle), accept/decline prompt (invite
 * pending), or the synced in-progress round (active game).
 */
export function GameSheet({
  gameInvite,
  activeGame,
  onStartGame,
  onAcceptGame,
  onDeclineGame,
  onNextPrompt,
  onRevealPrompt,
  onCloseGame,
  onClose,
}: GameSheetProps) {
  if (activeGame) {
    const { gameType, prompt, revealed } = activeGame;
    const game = GAMES[gameType];
    return (
      <CallSheet title={`${game.icon} ${game.label}`} onClose={onClose} testID="call-game-sheet">
        <ScrollView contentContainerStyle={styles.content}>
          <Text style={styles.promptText}>{prompt.text}</Text>

          {gameType === 'trivia' && prompt.options && (
            <View style={styles.optionsList}>
              {prompt.options.map((option) => {
                const isCorrect = revealed && option === prompt.correct_option;
                const isWrong = revealed && option !== prompt.correct_option;
                return (
                  <Pressable
                    key={option}
                    style={[
                      styles.optionButton,
                      isCorrect && styles.optionButtonCorrect,
                      isWrong && styles.optionButtonWrong,
                    ]}
                    onPress={onRevealPrompt}
                    disabled={revealed}
                  >
                    <Text style={[styles.optionText, isCorrect && styles.optionTextCorrect]}>
                      {isCorrect ? `✓  ${option}` : option}
                    </Text>
                  </Pressable>
                );
              })}
            </View>
          )}

          {gameType === 'trivia' && (
            <Text style={styles.attributionText}>{OPENTDB_ATTRIBUTION}</Text>
          )}
        </ScrollView>
        <View style={styles.footer}>
          <Pressable style={styles.secondaryButton} onPress={onCloseGame}>
            <Text style={styles.secondaryText}>End game</Text>
          </Pressable>
          <Pressable style={styles.primaryButton} onPress={onNextPrompt}>
            <Text style={styles.primaryText}>Next ›</Text>
          </Pressable>
        </View>
      </CallSheet>
    );
  }

  if (gameInvite) {
    const game = GAMES[gameInvite.gameType];
    if (gameInvite.fromSelf) {
      return (
        <CallSheet title="🎮 Mini games" onClose={onClose} testID="call-game-sheet">
          <View style={styles.centered}>
            <Text style={styles.bigIcon}>{game.icon}</Text>
            <Text style={styles.inviteTitle}>{game.label}</Text>
            <Text style={styles.inviteSubtitle}>Waiting for them to accept…</Text>
          </View>
        </CallSheet>
      );
    }
    return (
      <CallSheet title="🎮 Mini games" onClose={onClose} testID="call-game-sheet">
        <View style={styles.centered}>
          <Text style={styles.bigIcon}>{game.icon}</Text>
          <Text style={styles.inviteTitle}>Play {game.label}?</Text>
          <Text style={styles.inviteSubtitle}>Your match wants to play a game.</Text>
        </View>
        <View style={styles.footer}>
          <Pressable style={styles.secondaryButton} onPress={onDeclineGame}>
            <Text style={styles.secondaryText}>Decline</Text>
          </Pressable>
          <Pressable style={styles.primaryButton} onPress={onAcceptGame}>
            <Text style={styles.primaryText}>Accept</Text>
          </Pressable>
        </View>
      </CallSheet>
    );
  }

  return (
    <CallSheet title="🎮 Mini games" onClose={onClose} testID="call-game-sheet">
      <ScrollView contentContainerStyle={styles.content}>
        {(Object.keys(GAMES) as GameType[]).map((gameType) => {
          const game = GAMES[gameType];
          return (
            <Pressable
              key={gameType}
              style={({ pressed }) => [styles.pickerRow, pressed && styles.pickerRowPressed]}
              onPress={() => onStartGame(gameType)}
            >
              <View style={styles.pickerIcon}>
                <Text style={styles.pickerIconText}>{game.icon}</Text>
              </View>
              <View style={styles.pickerBody}>
                <Text style={styles.pickerTitle}>{game.label}</Text>
                <Text style={styles.pickerSubtitle}>{game.blurb}</Text>
              </View>
              <Text style={styles.chevron}>›</Text>
            </Pressable>
          );
        })}
      </ScrollView>
    </CallSheet>
  );
}

const styles = StyleSheet.create({
  content: {
    padding: 14,
    gap: 10,
  },
  promptText: {
    color: colors.text,
    fontSize: 17,
    lineHeight: 24,
    fontWeight: '600',
    marginBottom: 4,
  },
  attributionText: {
    color: colors.textMuted,
    fontSize: 11,
    marginTop: 4,
  },
  optionsList: {
    gap: 8,
  },
  optionButton: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 14,
    paddingHorizontal: 14,
    paddingVertical: 12,
  },
  optionButtonCorrect: {
    backgroundColor: colors.successSoft,
    borderColor: colors.success,
  },
  optionButtonWrong: {
    opacity: 0.5,
  },
  optionText: {
    color: colors.text,
    fontSize: 15,
  },
  optionTextCorrect: {
    color: colors.success,
    fontWeight: '600',
  },
  footer: {
    flexDirection: 'row',
    gap: 10,
    paddingHorizontal: 14,
    paddingTop: 10,
    paddingBottom: 24,
    borderTopWidth: 1,
    borderTopColor: '#26262f',
  },
  primaryButton: {
    flex: 1,
    backgroundColor: colors.primary,
    borderRadius: 999,
    paddingVertical: 12,
    alignItems: 'center',
  },
  primaryText: {
    color: colors.onPrimary,
    fontWeight: '700',
  },
  secondaryButton: {
    flex: 1,
    backgroundColor: colors.surface,
    borderRadius: 999,
    paddingVertical: 12,
    alignItems: 'center',
  },
  secondaryText: {
    color: colors.text,
    fontWeight: '600',
  },
  centered: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
    gap: 6,
  },
  bigIcon: {
    fontSize: 44,
    marginBottom: 6,
  },
  inviteTitle: {
    color: colors.text,
    fontSize: 18,
    fontWeight: '700',
  },
  inviteSubtitle: {
    color: colors.textMuted,
  },
  pickerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 16,
    padding: 14,
  },
  pickerRowPressed: {
    backgroundColor: colors.surfaceRaised,
  },
  pickerIcon: {
    width: 42,
    height: 42,
    borderRadius: 12,
    backgroundColor: colors.surfaceRaised,
    alignItems: 'center',
    justifyContent: 'center',
  },
  pickerIconText: {
    fontSize: 20,
  },
  pickerBody: {
    flex: 1,
  },
  pickerTitle: {
    color: colors.text,
    fontSize: 14,
    fontWeight: '600',
  },
  pickerSubtitle: {
    color: colors.textMuted,
    fontSize: 12,
    marginTop: 2,
  },
  chevron: {
    color: colors.textMuted,
    fontSize: 20,
  },
});
