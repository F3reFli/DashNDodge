"""Pre-boss banter. 'P' = player, 'B' = boss. Per-character overrides first,
then a generic fallback where {me} is the player's first name."""

DIALOGUES = {
    "rumia": {
        "default": [
            ("B", "Is that so~? A human, out walking in the dark?"),
            ("P", "I'm not walking. I'm dashing. There's a difference."),
            ("B", "Then are you a human I can eat... at high speed?"),
            ("P", "...I'm going to say no and hope that settles it."),
        ],
        "reimu": [
            ("B", "Is that so~? You look like a tasty shrine maiden."),
            ("P", "I'm mostly rice crackers and disappointment. Move."),
            ("B", "Mmm, crunchy~"),
        ],
        "marisa": [
            ("B", "Is that so~? A witch! Do witches taste like mushrooms?"),
            ("P", "Only on Tuesdays, ze. Outta my way!"),
        ],
        "cirno": [
            ("P", "Out of the way! The strongest is coming through!"),
            ("B", "Is that so~? ...Who?"),
            ("P", "ME! I'm the strongest! Have you been living under a rock?"),
            ("B", "I've been living in the dark. It's kinda like a rock."),
        ],
        "meiling": [
            ("B", "Is that so~? Aren't you supposed to be guarding a gate?"),
            ("P", "I'm on patrol! A very, very long patrol. Far from Sakuya-san."),
        ],
    },
    "cirno": {
        "default": [
            ("B", "HALT! This lake belongs to the strongest fairy in Gensokyo!"),
            ("P", "The lake you froze last week? With yourself stuck inside?"),
            ("B", "That was TRAINING! I'll freeze you solid, just like a frog!"),
        ],
        "cirno": [
            ("B", "Hey! You stole my face!"),
            ("P", "No, YOU stole MY face!"),
            ("B", "There can only be one strongest! Let's settle this!"),
            ("P", "⑨ versus ⑨! Fight!"),
        ],
        "marisa": [
            ("P", "Hey Cirno, can I borrow your lake? Just for a bit, ze."),
            ("B", "NO! You never give anything back! Daiyousei said so!"),
        ],
        "sakuya": [
            ("B", "Halt, maid! I'm the strongest!"),
            ("P", "I need ice for the Mistress's tea. You'll do nicely."),
            ("B", "...Wait, what?"),
        ],
        "remilia": [
            ("B", "A vampire! I'm not scared! I'm the STRONGEST!"),
            ("P", "How adorable. I'll keep you as an ice cube for my drinks."),
        ],
    },
    "meiling": {
        "default": [
            ("B", "Halt! Nobody passes the gate of the Scarlet Devil Mansion!"),
            ("P", "Weren't you snoring three seconds ago?"),
            ("B", "I was meditating! With my eyes closed! Loudly!"),
        ],
        "sakuya": [
            ("B", "S-Sakuya-san! I was totally awake! The gate is secure!"),
            ("P", "Meiling. There is drool on your hat. Again."),
            ("B", "...Okay, I'll fight you, but please go easy on the knives?"),
        ],
        "meiling": [
            ("B", "Wait. Who's guarding the gate if I'm here?"),
            ("P", "...Who's guarding the gate if I'M here?!"),
            ("B", "Nobody! Quick, let's fight and get back to work!"),
        ],
        "marisa": [
            ("B", "You again! You're NOT borrowing more books today!"),
            ("P", "Relax, I'm returning one. ...Kidding! Master Spark!"),
        ],
    },
    "patchouli": {
        "default": [
            ("B", "*cough* ...Visitors. In my library. Making noise."),
            ("P", "Is there a 'no dashing in the library' rule?"),
            ("B", "There is now. Seven elements. Zero patience. *cough*"),
        ],
        "marisa": [
            ("B", "You. Return my books. All eighty-seven of them."),
            ("P", "I'm just borrowing them until I die, ze! It's a long-term loan."),
            ("B", "Then let's shorten the term."),
        ],
        "cirno": [
            ("P", "Whoa, so many books! Do you have one about being the strongest?"),
            ("B", "...We have one about counting to ten. Would you like it?"),
            ("P", "Don't need it! I can count to ⑨!"),
        ],
        "reimu": [
            ("B", "The shrine maiden. Have you come to read, for once?"),
            ("P", "I came to stop the mist. And maybe nap in a quiet corner."),
        ],
    },
    "sakuya": {
        "default": [
            ("B", "Guests at this hour? The Mistress will want tea... and an explanation."),
            ("P", "Could you make the clock tower tick a little less ominously?"),
            ("B", "I'm afraid your time is mine now. Quite literally."),
        ],
        "sakuya": [
            ("B", "An impostor? In my uniform? And it's poorly ironed."),
            ("P", "It is NOT poorly ironed."),
            ("B", "Then let's settle this. On my time."),
        ],
        "meiling": [
            ("B", "Meiling. Why are you inside. Who is guarding the gate."),
            ("P", "Um. The gate is guarding itself? It's very independent!"),
            ("B", "Knives it is."),
        ],
        "cirno": [
            ("B", "A fairy. Fairies don't usually get this far."),
            ("P", "That's 'cause I'm the strongest! Also, I got lost."),
        ],
        "remilia": [
            ("B", "Mistress? Why are you fighting your way through your own house?"),
            ("P", "Boredom, Sakuya. Now entertain me."),
            ("B", "...As you wish."),
        ],
    },
    "remilia": {
        "default": [
            ("B", "So you're the one making all that racket downstairs."),
            ("P", "You're the one who covered the whole sky in red mist!"),
            ("B", "It's called an aesthetic. Now, shall we dance under the scarlet moon?"),
        ],
        "reimu": [
            ("P", "Turn the mist off. My laundry won't dry."),
            ("B", "Such a petty reason to fight a vampire."),
            ("P", "My laundry is NOT petty."),
        ],
        "sakuya": [
            ("B", "Sakuya? You're on the wrong side of this fight."),
            ("P", "Forgive me, Mistress. The mist is bad for the curtains."),
            ("B", "...Fair. Very well, show me what I'm paying you for."),
        ],
        "remilia": [
            ("B", "A mirror? How dare a mirror show my reflection. I'm a vampire!"),
            ("P", "That's not a mirror, that's me. The better me."),
            ("B", "Fate says only one of us is the real one."),
        ],
        "cirno": [
            ("P", "I'm here to beat you and become the strongest!"),
            ("B", "You're a fairy. On a mission. In MY throne room. How did--"),
            ("P", "I took a left at the lake!"),
        ],
    },
    "flandre": {
        "default": [
            ("B", "Ehehe~ Are you a new toy? Big sis never lets me play."),
            ("P", "I'm more of a 'dodges everything' kind of toy."),
            ("B", "Then let's see how long you last~! Don't break too fast, okay?"),
        ],
        "remilia": [
            ("B", "Big sis?! You came to play with me?!"),
            ("P", "Flandre, you're grounded for another 495 years."),
            ("B", "Then I'll play with you RIGHT NOW!"),
        ],
        "meiling": [
            ("B", "Meiling! You came all the way down here!"),
            ("P", "Please don't blow up the gate again, I just fixed it..."),
        ],
    },
}


def lines_for(boss_id, player_id):
    entry = DIALOGUES.get(boss_id, {})
    return entry.get(player_id) or entry.get("default", [])
