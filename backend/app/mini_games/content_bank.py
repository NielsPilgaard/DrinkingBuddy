"""Static would-you-rather / never-have-I-ever prompt bank
(tasks/mini-games.md). Authored directly rather than scraped from the thin
unofficial WYR/NHIE APIs referenced in the task spec - same end state (a
self-hosted, no-live-third-party-dependency, pre-vetted bank seeded into
`game_prompts`), without depending on sources of unknown size/reliability.
Content is deliberately kept light/pub-conversation-safe; the DB row is the
editable source of truth post-seed, this list only seeds it once."""

WOULD_YOU_RATHER_PROMPTS: list[str] = [
    "Would you rather always be 10 minutes late or always be 20 minutes early?",
    "Would you rather have unlimited free travel or unlimited free food?",
    "Would you rather be able to speak every language or play every instrument?",
    "Would you rather live without music or live without TV/movies?",
    "Would you rather have a rewind button or a pause button for your life?",
    "Would you rather be famous for something embarrassing or unknown forever?",
    "Would you rather always know when someone is lying or always get away with lying?",
    "Would you rather explore space or explore the deep ocean?",
    "Would you rather lose your sense of smell or your sense of taste?",
    "Would you rather have a personal chef or a personal driver?",
    "Would you rather be able to talk to animals or speak every human language?",
    "Would you rather live in a treehouse or a houseboat?",
    "Would you rather never use social media again or never watch another movie?",
    "Would you rather always have to sing instead of speak or dance everywhere you walk?",
    "Would you rather have the ability to fly or be invisible?",
    "Would you rather relive your favorite memory forever or make a new one every day?",
    "Would you rather have free coffee for life or free drinks for life?",
    "Would you rather be stuck in a lift with your boss or a stranger?",
    "Would you rather have more time or more money?",
    "Would you rather never be able to lie or never be able to keep a secret?",
    "Would you rather live in a world without winter or without summer?",
    "Would you rather be the funniest person in the room or the smartest?",
    "Would you rather go back in time 10 years or forward 10 years?",
    "Would you rather have a photographic memory or be a genius at math?",
    "Would you rather give up your phone for a month or give up alcohol for a year?",
]

NEVER_HAVE_I_EVER_PROMPTS: list[str] = [
    "Never have I ever gone skinny dipping.",
    "Never have I ever sung karaoke in public.",
    "Never have I ever ghosted someone.",
    "Never have I ever pretended to be sick to skip work or school.",
    "Never have I ever sent a text to the wrong person.",
    "Never have I ever fallen asleep in a public place.",
    "Never have I ever cried during a movie.",
    "Never have I ever lied about my age.",
    "Never have I ever gone on a blind date.",
    "Never have I ever forgotten someone's name right after meeting them.",
    "Never have I ever stalked an ex on social media.",
    "Never have I ever laughed so hard I cried.",
    "Never have I ever eaten food off the floor.",
    "Never have I ever pretended to like a gift I hated.",
    "Never have I ever gotten lost in a foreign city.",
    "Never have I ever danced in front of a mirror pretending I was performing.",
    "Never have I ever binged an entire TV series in one day.",
    "Never have I ever talked to myself out loud in public.",
    "Never have I ever accidentally liked an old photo while stalking someone's profile.",
    "Never have I ever shown up to an event on the wrong day.",
    "Never have I ever pretended to know a song I'd never heard before.",
    "Never have I ever tripped and fallen in front of a crowd.",
    "Never have I ever had a crush on a friend's partner.",
    "Never have I ever left the house with mismatched socks or shoes.",
    "Never have I ever sent a risky text and immediately regretted it.",
]
