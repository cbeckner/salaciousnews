// data.jsx — shared content for both directions. Real headlines pulled from
// the live salacious.news so the mock reads true. Exported to window.

const CATS = ["US", "World", "Technology", "Entertainment", "Sports", "Politics", "Other"];

// img: short caption describing what the photo SHOULD be (drives placeholders)
const A = (id, cat, title, source, date, dek, img) => ({ id, cat, title, source, date, dek, img });

const ARTICLES = {
  lead: A("lead", "Entertainment",
    "$200 Million Flop — He-Man's Box Office Bloodbath",
    "Forbes", "Mon, Jun 8, 2026",
    "Amazon's $200M 'Masters of the Universe' bombs at the box office, forcing a panicked pivot to paid streaming — a humiliation for Jared Leto and the streaming giant.",
    "He-Man on a crumbling box-office throne"),

  trending: [
    A("t1", "Entertainment", "Voice Vanishes on Tour — Charlie Puth's Health Crisis Deepens", "TMZ", "Mon, Jun 8, 2026", "", "Charlie Puth gripping a silent microphone"),
    A("t2", "Entertainment", "Elmo's Final Four Fumble — Exiled by His Own City", "BBC News", "Sun, Jun 7, 2026", "", "Elmo benched courtside, head down"),
    A("t3", "Entertainment", "Swift's Secret Garden Wedding — Will Mahomes Crash the Bride Squad?", "inTouch Weekly", "Sun, Jun 7, 2026", "", "Lavish garden wedding arch at dusk"),
    A("t4", "Business", "China's Robot Army Has No One to Serve — An Awkward Silence", "Associated Press", "Sun, Jun 7, 2026", "", "Rows of idle service robots in an empty mall"),
    A("t5", "Politics", "Did Trumpworld Time the Market? A $1.5B Bet and the Watchdog That Hit Snooze", "CBS News", "Fri, Apr 3, 2026", "", "Trading floor screens glowing red"),
  ],

  feed: [
    A("f1", "Entertainment", "Hollywood Horror — 'Man of Sin' Slain by Girlfriend's Son", "Santa Rosa Press Democrat", "Sat, Jun 6, 2026", "Detectives say a routine domestic call uncovered a scene straight out of a screenplay nobody wanted produced.", "Yellow police tape across a Hollywood bungalow"),
    A("f2", "Politics", "TRUMP'S CONCERT MELTDOWN! All-Star Lineup Bails, 'Freedom 250' Becomes a Rally of One", "Rolling Stone", "Fri, Jun 5, 2026", "Headliners vanished in a mass exodus, leaving a single, very familiar name on the marquee.", "Empty stadium stage, one spotlight"),
    A("f3", "Entertainment", "Biermann's X-Rated Nightmare — Kim Zolciak's Shock Court Bombshell", "Page Six", "Thu, Jun 4, 2026", "New filings allege scenes the neighbors could reportedly hear from the driveway.", "Courthouse steps swarmed by cameras"),
    A("f4", "Politics", "Iran's New Strikes Drop as Trump Dangles a NATO Exit — Oil Soars, Markets Swoon", "CBS News", "Fri, Apr 3, 2026", "A murky timeline, a $1.5B bet, and a watchdog that apparently hit snooze.", "Oil derrick silhouetted against a red sky"),
    A("f5", "Technology", "Elon Musk Just Pulled the Plug — Tesla's Model S and X Are Over", "The Verge", "Fri, Apr 3, 2026", "Only about 600 are left worldwide. You won't believe what happens to the last one.", "Lone Tesla Model S under a showroom spotlight"),
    A("f6", "US", "Measles Meltdown — South Carolina's Supersized Outbreak Sends a Coast-to-Coast Wake-Up Call", "The Washington Post", "Sun, Feb 1, 2026", "Record numbers, every state on notice, and a question nobody wants to answer.", "Crowded clinic waiting room"),
  ],

  byCat: {
    World: [
      A("w1", "World", "Top Afghanistan General Unleashes Torrent of Tearful Regrets in Exclusive Confessional", "Fox News", "Sat, Sep 9, 2023", "'I have a lot of regrets,' he says — and then the accusations start flying.", "Decorated general mid-interview, eyes down"),
      A("w2", "World", "You Won't Believe What Just Shook Morocco to Its Core!", "Reuters", "Fri, Sep 8, 2023", "", "Cracked old-city wall after the quake"),
      A("w3", "World", "Prince Harry's Jaw-Dropping Spectacle — The Invictus Games Turn Upside Down!", "BBC News", "Thu, Sep 7, 2023", "", "Harry cheering in a packed stadium"),
      A("w4", "World", "Panama's Scandalously Express Deportation Ramp-Up Battles Record Migration Tides", "AP", "Wed, Sep 6, 2023", "", "Line of migrants at a jungle checkpoint"),
    ],
    US: [
      A("u1", "US", "America's Measles Wake-Up Call — South Carolina's Outbreak Shatters Records", "The Washington Post", "Sun, Feb 1, 2026", "", "Vaccine vials on a steel tray"),
      A("u2", "US", "Breathtaking Close-Call in Texas — Gator Stalks Kiddies in Packed Public Lake!", "Fox News", "Wed, Sep 13, 2023", "", "Alligator eyes above murky lake water"),
      A("u3", "US", "Apocalypse Now — The Standoff Fully Paralyzing the Auto Industry", "CNN", "Wed, Sep 13, 2023", "", "Silent auto assembly line"),
      A("u4", "US", "Grocery Apocalypse Now — Is Your Wallet Next on the Chopping Block?", "CNN", "Wed, Sep 13, 2023", "", "Receipt longer than the cart"),
    ],
    Technology: [
      A("te1", "Technology", "You Won't Believe How Hackers Turned Axios Into a Trojan Horse Overnight", "Wired", "Thu, Apr 2, 2026", "", "Laptop screen full of cascading code"),
      A("te2", "Technology", "OpenAI's $122B Shockwave — The VIP Investor List and Pre-IPO Tea, Spilled", "The Information", "Wed, Apr 1, 2026", "", "Glass HQ lobby with logo wall"),
    ],
    Sports: [
      A("s1", "Sports", "Clash of the Titans — Spain and Sweden Battle for World Cup Glory", "ESPN", "Tue, Aug 15, 2023", "", "Players colliding for a header"),
      A("s2", "Sports", "Scandalous Drama — Women's World Cup Clash Leaves Fans Shaken", "BBC Sport", "Mon, Aug 14, 2023", "", "Stunned fans in team colors"),
    ],
  },

  // "Around the Web" advertorial bait — high-RPM native ad row
  advertorial: [
    { id: "ad1", label: "Sponsored", title: "Doctors Stunned: This $3 Kitchen Trick Melts Belly Fat Overnight", brand: "HealthDailyPro", img: "Steaming mug on a rustic table" },
    { id: "ad2", label: "Sponsored", title: "She Bought an Old Painting for $4 — Appraisers Couldn't Stay Calm", brand: "TrendingFinds", img: "Ornate frame under gallery light" },
    { id: "ad3", label: "Sponsored", title: "Why Everyone in Your Zip Code Is Switching to This Solar Plan", brand: "EnergySaverUSA", img: "Solar panels at golden hour" },
    { id: "ad4", label: "Sponsored", title: "Vets Beg Owners to Stop Feeding Dogs This One Common Food", brand: "PetWellnessHub", img: "Hopeful dog at the dinner table" },
  ],
};

Object.assign(window, { CATS, ARTICLES });
