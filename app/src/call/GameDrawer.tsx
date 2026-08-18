import { Pressable, type StyleProp, StyleSheet, Text, View, type ViewStyle } from 'react-native';
import type { GamePrompt, GameType } from './signaling';

const GAME_LABELS: Record<GameType, string> = {
  trivia: 'Trivia',
  would_you_rather: 'Would You Rather',
  never_have_i_ever: 'Never Have I Ever',
};

type GameDrawerProps = {
  style?: StyleProp<ViewStyle>;
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
 * Drawer for the "play game" call action (tasks/mini-games.md). Renders one
 * of three states: game picker (idle), accept/decline prompt (invite
 * pending), or the synced in-progress round (active game) - only one is ever
 * shown, mirroring how the chat/menu drawers in
 * docs/mockups/prototype-match-screen.html are mutually exclusive.
 */
export function GameDrawer({
  style,
  gameInvite,
  activeGame,
  onStartGame,
  onAcceptGame,
  onDeclineGame,
  onNextPrompt,
  onRevealPrompt,
  onCloseGame,
  onClose,
}: GameDrawerProps) {
  if (activeGame) {
    const { gameType, prompt, revealed } = activeGame;
    return (
      <View style={[styles.drawer, style]}>
        <View style={styles.header}>
          <Text style={styles.title}>{GAME_LABELS[gameType]}</Text>
          <Pressable onPress={onClose}>
            <Text style={styles.closeText}>︿</Text>
          </Pressable>
        </View>

        <Text style={styles.promptText}>{prompt.text}</Text>

        {gameType === 'trivia' && prompt.options && (
          <View style={styles.optionsList}>
            {prompt.options.map((option) => {
              const isCorrect = revealed && option === prompt.correct_option;
              return (
                <Pressable
                  key={option}
                  style={[styles.optionButton, isCorrect && styles.optionButtonCorrect]}
                  onPress={onRevealPrompt}
                  disabled={revealed}
                >
                  <Text style={styles.optionText}>{option}</Text>
                </Pressable>
              );
            })}
          </View>
        )}

        {gameType === 'trivia' && <Text style={styles.attributionText}>{OPENTDB_ATTRIBUTION}</Text>}

        <View style={styles.actionsRow}>
          <Pressable style={styles.actionButton} onPress={onNextPrompt}>
            <Text style={styles.actionText}>Next</Text>
          </Pressable>
          <Pressable style={[styles.actionButton, styles.endButton]} onPress={onCloseGame}>
            <Text style={styles.actionText}>End game</Text>
          </Pressable>
        </View>
      </View>
    );
  }

  if (gameInvite) {
    if (gameInvite.fromSelf) {
      return (
        <View style={[styles.drawer, style]}>
          <Text style={styles.title}>{GAME_LABELS[gameInvite.gameType]}</Text>
          <Text style={styles.promptText}>Waiting for them to accept…</Text>
        </View>
      );
    }
    return (
      <View style={[styles.drawer, style]}>
        <Text style={styles.title}>Play {GAME_LABELS[gameInvite.gameType]}?</Text>
        <View style={styles.actionsRow}>
          <Pressable style={styles.actionButton} onPress={onAcceptGame}>
            <Text style={styles.actionText}>Accept</Text>
          </Pressable>
          <Pressable style={[styles.actionButton, styles.endButton]} onPress={onDeclineGame}>
            <Text style={styles.actionText}>Decline</Text>
          </Pressable>
        </View>
      </View>
    );
  }

  return (
    <View style={[styles.drawer, style]}>
      <View style={styles.header}>
        <Text style={styles.title}>Mini games</Text>
        <Pressable onPress={onClose}>
          <Text style={styles.closeText}>︿</Text>
        </Pressable>
      </View>
      {(Object.keys(GAME_LABELS) as GameType[]).map((gameType) => (
        <Pressable key={gameType} style={styles.pickerRow} onPress={() => onStartGame(gameType)}>
          <Text style={styles.pickerText}>{GAME_LABELS[gameType]}</Text>
        </Pressable>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  drawer: {
    position: 'absolute',
    bottom: 96,
    left: 12,
    right: 12,
    backgroundColor: 'rgba(23,23,29,0.95)',
    borderRadius: 12,
    padding: 16,
    gap: 12,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  title: {
    color: '#f2f2f5',
    fontWeight: '600',
    fontSize: 15,
  },
  closeText: {
    color: '#8a8a96',
    fontSize: 18,
  },
  promptText: {
    color: '#f2f2f5',
    fontSize: 15,
    lineHeight: 21,
  },
  attributionText: {
    color: '#8a8a96',
    fontSize: 11,
  },
  pickerRow: {
    backgroundColor: '#1f1f28',
    borderRadius: 8,
    paddingHorizontal: 14,
    paddingVertical: 12,
  },
  pickerText: {
    color: '#f2f2f5',
    fontWeight: '600',
  },
  optionsList: {
    gap: 8,
  },
  optionButton: {
    backgroundColor: '#1f1f28',
    borderRadius: 8,
    paddingHorizontal: 14,
    paddingVertical: 10,
  },
  optionButtonCorrect: {
    backgroundColor: '#1f4d3a',
  },
  optionText: {
    color: '#f2f2f5',
  },
  actionsRow: {
    flexDirection: 'row',
    gap: 8,
  },
  actionButton: {
    backgroundColor: '#2563eb',
    borderRadius: 8,
    paddingHorizontal: 14,
    paddingVertical: 10,
  },
  endButton: {
    backgroundColor: '#ff6b6b',
  },
  actionText: {
    color: '#fff',
    fontWeight: '600',
  },
});
