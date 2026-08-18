# Server-side mirror of app/src/content/iceBreakers.ts (tasks/ice-breaker.md).
# The client bundles the same static list, but the server must validate
# against its own copy - trusting a client-supplied ice_breaker `text` field
# verbatim would let a peer relay arbitrary freeform text through a channel
# that's deliberately exempt from chat_safety scanning. Keep in sync with
# the client list by hand; both are static/build-time content.
ICE_BREAKERS: frozenset[str] = frozenset(
    {
        "What's the most underrated drink you've ever had?",
        "Beach vacation or mountain cabin?",
        "What's a hobby you'd pick up if money/time weren't an issue?",
        "Dogs, cats, or neither?",
        "What's the last show you binged?",
        "What's your go-to karaoke song?",
        "Coffee person or tea person?",
        "What's a food combo you love that sounds weird to others?",
        "Morning person or night owl?",
        "What's the best concert or live show you've been to?",
        "Window seat or aisle seat?",
        "What's a skill you're low-key proud of?",
        "Sweet, salty, or sour snacks?",
        "What's a place you'd move to if you had to leave tomorrow?",
        "Texting or calling?",
        "What's the last thing that made you laugh out loud?",
        "Summer or winter?",
        "What's a small thing that instantly improves your day?",
        "Books or podcasts?",
        "What's your comfort food?",
        "City life or countryside?",
        "What's a trip you're still dreaming about?",
        "Early riser or late sleeper?",
        "What's your favorite way to unwind after a long day?",
        "Sweet drinks or bitter drinks?",
        "What's a movie you can rewatch endlessly?",
        "Planner or spontaneous?",
        "What's the weirdest job you've ever had?",
        "Board games or video games?",
        "What's something you learned recently that stuck with you?",
    }
)
