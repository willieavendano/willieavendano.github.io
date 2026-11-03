# Voice-clone reading script

A reading script for recording the ElevenLabs Professional Voice Clone that will narrate the Physics Manim videos and the Computer Science Math screen tutorials. Parts B and C are the real narration from videos already published or built, so the clone learns the exact register it will be asked to reproduce. Parts A and D add range: letters, numbers, symbols, questions, asides.
**Total: about 6,147 words, roughly 35 minutes at the narrator's 2.9 words per second.**


## Before you press record

- **Target length:** 35 to 40 minutes of clean speech. ElevenLabs needs 30 minutes minimum for a Professional clone and improves up to about 3 hours. This script is about 35 minutes at narration pace, so one careful read clears the floor; real speech with pauses and restarts usually lands near 40. If you have time, read Part B a second time to get toward an hour.
- **Room and mic:** quiet room, soft surfaces, no fan or HVAC, phone in another room. Mic 15 to 20 cm from your mouth, slightly off-axis to dodge plosives. Headphones off or very low. The same mic for every chunk.
- **Format:** record at 44.1 or 48 kHz, 24-bit WAV if you can. Leave the levels peaking around minus 12 dB. No noise reduction, no EQ, no compression, no music. ElevenLabs does its own cleanup, and processing makes the clone sound processed.
- **Delivery:** read the way the videos sound. Steady, warm, a half-step slower than conversation, with real pauses at periods. Do not perform. Do not rush numbers. Say letters as letters ("A P Y", "B three"), exactly as written, and read numbers written as words exactly as written ("six fifty one eighty four"), because that is how the engine will be asked to say them.
- **Mistakes:** do not stop the recorder. Pause two seconds, then re-read the whole sentence from its start. The long pause is easy to find and cut later, or you can leave it; ElevenLabs tolerates it.
- **Chunks:** record in four files, one per Part, with a sip of water between. Chunk count does not matter to ElevenLabs. Total runtime does.
- **One speaker only.** No room tone with other voices, no replies to anyone, no phone notification.
- **Upload:** ElevenLabs, Voices, Add a new voice, Professional Voice Clone. Upload all four files, complete the identity verification, and let it train (a few hours). Then copy the voice ID and set `ELEVEN_VOICE_ID` on each machine; both pipelines read it and will re-voice from the cache on the next build.


## Part A · Warm-up and range

*About 412 words · 2 min at narration pace.*

Read at a natural classroom pace. The odd sentences are on purpose; they cover sounds the lessons rarely use.

Good morning. Before we start, phones face down, calculators out, and somebody open a window.

Here is the plan for today: one idea, one worked example, one trap, and then you try it.

The quick brown fox jumps over the lazy dog, which is a sentence that uses every letter, and it is also a reasonable description of a projectile.

Zero, one, two, three, four, five, six, seven, eight, nine, ten. Eleven, twelve, thirteen, fourteen, fifteen, twenty, thirty, forty, fifty, one hundred, one thousand, one million.

Three point one four one five nine. Two point seven one eight. Nine point eight meters per second squared. Four point five percent. Six point nine percent. Sixteen thousand dollars.

A, B, C, D, E, F, G. H, I, J, K. L, M, N, O, P. Q, R, S. T, U, V. W, X, Y, and Z. Cell A one. Cell B three. Column F. Row twelve. Sheet one, exclamation point, B eight.

Equals. Plus. Minus. Times. Divided by. Open parenthesis. Close parenthesis. Caret, to the power of. Less than or equal to. Not equal to.

Why does that matter? Because the sign tells you the direction, and the direction is the whole answer.

Wait, hold on. Look at the units. Meters per second, times seconds, gives meters. If you got meters squared, something went wrong three lines ago.

Let's be honest about this one. Everybody gets it wrong the first time. The point is to get it wrong here, out loud, where it is cheap.

Judge, pledge, church, measure, vision, thing, think, three, these, those, father, bother, rather, weather, whether.

Strengths, twelfths, sixths, glimpsed, texts, worlds, months, thousandths.

Here is the picture. Here is the equation. Here is the number. Now, here is the question I actually care about: does the number make sense?

Pause. Breathe. Read the problem again. What is given? What is asked? What connects them?

Good. Now do the next one without me.

Okay, that one was rough. That is fine. Rough is where learning lives. Erase it, and go again.

Yes! That is exactly it. Say it one more time so the back row hears it.

No, not quite. Close. Look at the exponent. One twelfth, not twelve.

Remember, the deliverable is due Thursday, November twelfth, at the start of class, uploaded to the portal, as a P D F.

If you have a question later tonight, email me. I will answer before the bus leaves in the morning. Probably.


# Part B · Physics narration (Manim videos)

These are the scripts of the Unit 0 and Unit 1 videos as rendered. Each paragraph is one spoken beat. Read them as if the animation is on screen in front of you.


## Vectors & Components  ·  `PHY-U0-vectors-components`

*About 307 words · 2 min at narration pace.*

Every GPS route, every airplane heading, every pass a quarterback throws comes down to one move: taking an arrow, and breaking it into two pieces. Let's learn that move.

A delivery drone lifts off from South Beach and flies five kilometers, in a straight line, thirty-seven degrees north of east. That arrow is its displacement: how far it went, and in which direction.

Now ask a different question. How far east did it actually get? And how far north? Drop a line straight down from the tip, and the arrow splits into two pieces: an east piece, which we'll call x, and a north piece, y. And notice what just appeared. A right triangle.

A right triangle means your old friend SOH CAH TOA is back. But don't think of it as formulas to memorize. Those are just names for the sides of this triangle. The side touching the angle is the adjacent. The side across from the angle is the opposite. And the arrow itself, the longest side, is the hypotenuse.

Start with the east piece. It's adjacent to the angle, and adjacent means cosine. Cosine of thirty-seven degrees is adjacent over hypotenuse. So the adjacent side is five kilometers times the cosine of thirty-seven degrees. About four kilometers east.

The north piece sits opposite the angle, and opposite means sine. Five kilometers times the sine of thirty-seven degrees. About three kilometers north.

Four, three, five. That's the famous three four five right triangle, and it's exactly why physics teachers love thirty-seven degrees. One arrow pointing off at an angle just became two simple numbers. Four east. Three north.

Remember this move. Any time something travels at an angle, a kicked ball, a launched coconut, you break it into components first. Cosine for the side that touches the angle. Sine for the side across from it.


## Motion Graphs  ·  `PHY-U1-motion-graphs`

*About 467 words · 3 min at narration pace.*

Every moving thing, from a roller coaster to a car merging onto I ninety five, leaves behind the same three fingerprints. Three graphs. And here's the secret. They aren't three separate stories. Each one is the slope of the one above it. Let's watch it happen.

Meet the cart. Underneath it, three graphs sharing one clock. Position versus time. Velocity versus time. And acceleration versus time. A dot on each graph will trace out exactly what the cart is doing.

Run one. The cart rolls at a steady two meters per second. Position climbs in a straight ramp, the same distance every second. Velocity is a flat line at two. And acceleration? Sitting on zero. Nothing is changing, so nothing is accelerating.

Now look at that ramp. Go over two seconds, up four meters. Four meters in two seconds is two meters per second. The slope of the position graph is the velocity. That's the whole idea. Everything else is just this, again.

Run two. Same cart, but now it starts from rest and speeds up, two meters per second squared. Every second, its velocity grows by two. Watch the top graph bend. It curves upward, because every second the cart covers more ground than the last. Velocity is a straight ramp. Acceleration is a flat line above zero.

Freeze it at one second. Lay a tangent line on the position curve. Its slope is two meters per second. Now carry that number down. There it is, on the velocity graph. Same number, one floor lower.

Again, at four seconds. The tangent is much steeper. Its slope is eight meters per second. And the velocity point sits way higher. Steeper slope up top, taller point below.

One floor down, same trick. Take the slope of the velocity ramp. Up six meters per second, over three seconds. That's two meters per second squared. And that is exactly the height of the acceleration line. So uniform acceleration has a signature. A flat a t line. A straight v t ramp. A curved x t graph.

Run three. This is the one that trips people up. The cart starts at eight meters per second, with an acceleration of negative two. Position keeps rising, but flatter and flatter. Velocity ramps down. And the acceleration line sits below zero.

So does negative acceleration mean moving backward? No. Look at the cart. It never turns around. Velocity stays positive until the cart stops at four seconds. Acceleration doesn't tell you which way you're going. It tells you how your velocity is changing. When v and a have opposite signs, you're slowing down.

So here's the chain. Position, velocity, acceleration. Each graph is the slope of the one above it. Next time you see a curve, don't just look at it. Take its slope.


## The Kinematic Equations  ·  `PHY-U1-kinematic-equations`

*About 601 words · 3 min at narration pace.*

Four equations. Most people meet them as four things to memorize and forget by Friday. Here is something better. They are not four ideas. They are one picture. Once you see it, you can rebuild all four in ten seconds.

Here is the picture. Velocity up, time across. Constant acceleration means velocity changes by the same amount every second. So the graph is a straight line. A ramp. It starts at v initial and climbs to v final.

The slope of that ramp is the acceleration. Run across for a time t, and velocity rises by a times t. So v final equals v initial plus a times t. Equation one, read straight off the picture.

Now the big move. Displacement is velocity times time. Slice the time into thin strips. Each strip is velocity times a tiny time: a tiny displacement. Stack them up: the total displacement is the area under the ramp. Not like the area. It is the area.

That area is two shapes you already know. A rectangle, v initial tall and t wide: v initial times t. Plus a triangle on top, base t, height a times t: one half t times a t. Add them: delta x equals v initial t plus one half a t squared. Equation two.

Same area, seen another way. The whole shape is a trapezoid. Its area is average height times width, and the average height is halfway between v initial and v final. So delta x equals one half of v initial plus v final, times t. Equation three.

Equation four is the odd one. Take one and two and eliminate t with algebra. Out comes v final squared equals v initial squared plus two a delta x. No new picture, just time squeezed out.

So why four? Every kinematics problem has five variables: v initial, v final, a, t, and delta x. You know three and want a fourth. That leaves one you neither know nor want, and each equation omits exactly one. One has no delta x. Two, no v final. Three, no a. Four, no t. Pick the equation without your missing variable. That is the E in K D E A.

Let's run one. A car starts from rest and accelerates at three point oh meters per second squared for eight point oh seconds. How far does it go?

K, what do you know. v initial is zero. a is three point oh meters per second squared. t is eight point oh seconds. D, what don't you know. Delta x, in meters. So what's missing? v final. Not known, not asked for.

E. The equation with no v final. Delta x equals v initial t plus one half a t squared.

A. Symbols first, then numbers with units. Zero times eight: gone. One half, times three point oh, times eight squared, which is sixty four. One point five times sixty four: ninety six. Delta x equals ninety six meters. And the units: meters per second squared times seconds squared leaves meters. It checks itself.

Now look at the picture. v initial is zero, so the rectangle is gone. One triangle is left: base eight point oh seconds, height twenty four meters per second. One half times eight times twenty four. Ninety six meters. It was the area all along.

One warning. All of this came from a straight ramp. If acceleration changes, the ramp bends, the triangle is gone, and all four equations fail. Constant acceleration only. Check that first, every time.

Straight ramp. Slope is a. Area is delta x. Four equations, one picture.


## Free Fall  ·  `PHY-U1-free-fall`

*About 619 words · 4 min at narration pace.*

Nineteen seventy one. Apollo fifteen. Astronaut David Scott stands on the Moon, a hammer in one hand, a falcon feather in the other. He lets go. No air up there. They land together.

On Earth the feather lags, but only because of the air. Remove the air, and the hammer, the feather, a bowling ball, you, all fall exactly the same way. Mass does not matter.

One sentence. Free fall is not a new topic. It is uniform acceleration with the acceleration already filled in. Near Earth's surface, g is about nine point eight meters per second squared, pointing down. Same for everything.

Let me make that number visible. Drop a ball, and take a snapshot every second.

After one second, it has fallen four point nine meters. After two, nineteen point six. After three, forty four point one. Look at the gaps. They keep growing.

Now the velocity arrow. Every second it grows by the same nine point eight meters per second. Nine point eight, nineteen point six, twenty nine point four. Velocity against time is a straight ramp, and its slope is g. That is what meters per second squared means.

So the four kinematic equations from week two still work, exactly as written. a becomes g, delta x becomes delta y. Same selection rule: find the variable you do not have, pick the equation that leaves it out.

Pick a direction before you start. I recommend up is positive. Then g is negative nine point eight meters per second squared for the entire flight. Going up, negative. At the top, negative. Coming down, still negative. Velocity changes sign at the peak. Acceleration never does.

Let's run it. An egg, thrown straight up at fourteen point oh meters per second from the ground. How high does it go? How long is it in the air? Two questions, two K D E A passes.

Part a. K, what do you know? v initial, fourteen point oh meters per second. g, negative nine point eight. And the piece students miss: at the top, v final is zero. Write it down.

D, what don't you know? Delta y, in meters. E, which equation? Nobody gave you a time, so pick the one with no t. v final squared equals v initial squared plus two g delta y.

A, the algebra. Symbols first: delta y equals negative v initial squared over two g. Now numbers. Negative fourteen squared, negative one ninety six. Two times negative nine point eight, negative nineteen point six. Negative over negative is positive: ten point oh meters, straight up.

Now freeze. The egg is at the top. Velocity, zero. So what is the acceleration? Most missed question in the unit. It is not zero. It is still negative nine point eight. If acceleration were zero, velocity would stay zero, and the egg would hang there forever. It doesn't. Gravity never took a break. Down it comes.

Part b. Start K fresh. v initial, fourteen point oh. g, negative nine point eight. New known: delta y is zero, the egg lands where it started. D, time in seconds. E, no v final this time: delta y equals v initial t plus one half g t squared.

A. Zero equals fourteen t minus four point nine t squared. Factor out a t. Two answers. t equals zero, the launch. And t equals fourteen over four point nine, about two point eight six seconds. The landing.

Recap. Free fall is uniform acceleration with the number already filled in. Up is positive, g is negative nine point eight the whole flight. Mass does not matter. Same four equations, same K D E A. One new number, and now you know it.


## Projectile Motion  ·  `PHY-U1-projectile-decomposition`

*About 609 words · 4 min at narration pace.*

Picture a seawall in Miami, fifteen meters above the water. Two coconuts sit on the edge. I drop one. At the exact same instant, I fire the other one straight out, sideways. Which coconut hits the water first?

Watch them. Same height. Same height. Same height. They splash down at the same moment. The one flying sideways still falls exactly like the one that was dropped. Gravity pulls down. It does not pull sideways. Moving sideways neither helps the fall nor fights it.

So here is the whole trick. Horizontal motion: no acceleration, constant velocity. Vertical motion: free fall, with g. Two separate motions, happening at the same time, to the same object. The only thing they share is the clock.

Now launch one at an angle, and freeze it at a few instants. At every freeze, the velocity splits into two pieces. The horizontal piece, v x, is the same length every single time. The vertical piece, v y, shrinks on the way up, hits zero at the very top, and grows back downward on the way down. That vertical piece is the only thing gravity touches.

Look at it as two shadows. The shadow on the ground moves with even spacing. That is constant velocity. The shadow on the wall moves with free fall spacing, bunched up near the top, spreading out as it falls. Put the two shadows back together, instant by instant, and you get the arc. The parabola is nothing more than those two motions glued together by time.

Which means every projectile problem starts with a move you already own from Workshop Three. The launch velocity is a vector. Break it into components first. v x is v times cosine of theta. v y is v times sine of theta. Adjacent, cosine. Opposite, sine. Same triangle as always.

Let's do a real one. A coconut is launched from a fifteen point oh meter seawall at twelve point oh meters per second, twenty-five degrees above the horizontal. How far from the base of the wall does it splash down?

Decompose first. v x is twelve point oh times cosine of twenty-five degrees, about ten point nine meters per second. v initial y is twelve point oh times sine of twenty-five degrees, about five point oh seven meters per second. From this moment on, those two numbers live in separate columns.

Vertical column, K D E A. Known: v initial y is five point oh seven, delta y is negative fifteen point oh, because it lands below where it started, and g is negative nine point eight. Don't know: time. Equation: the one with no v final y. Algebra: negative fifteen equals five point oh seven t minus four point nine t squared. That's a quadratic. Take the positive root. t is about two point three four seconds.

Now that time crosses the bridge into the horizontal column. Known: v x is ten point nine, and t is two point three four. Equation: delta x equals v x times t. Nothing else, because there is no horizontal acceleration. Ten point nine times two point three four. About twenty-five point five meters. Watch it fly. Splash.

Here is the trap, and almost everyone falls in once. Twelve point oh meters per second does not belong in the vertical equation. Neither does v x. And no g ever goes in the horizontal equation. x numbers stay in the x column. y numbers stay in the y column. Two columns. Two K D E A passes. One t crossing between them.

Horizontal: constant. Vertical: gravity. Time is the only thing they share. That independence is the whole trick.


# Part C · Cornerstone II screen tutorial (Computer Science Math)

The narration of *Save for the Car: building the model*, chapter by chapter. Each paragraph is one scene; the spreadsheet is being built while you speak.


## Chapter 0 · What we're building

*About 148 words · 1 min at narration pace.*

You picked a car in October. Sixteen thousand dollars, out the door. Here's the question for Thursday, November twelfth: if you save first, how much less do you borrow, and what does the loan really cost you?

One workbook, two sheets. Savings grows your money month by month in a high yield savings account. Loan takes that balance as the down payment and finances the rest. The same compounding machine, first paying you, then charging you.

Every sheet uses one layout. Labels in column A. Inputs, the numbers you're allowed to change, in column B. Everything else is a formula pointing at those inputs. Never type the same number twice.

That's the Formula Honesty line on the rubric: change an input live, and everything moves. Every rate here is a fictional classroom value. Build the sample first, matching mine to the cent, then swap in your own car.


## Chapter 1 · Savings sheet: the inputs and the monthly rate

*About 351 words · 2 min at narration pace.*

Inputs start in row two. Initial savings: the money you have on day one. The class sample is a fictional five hundred dollars. Label in column A, number in column B.

B three is the A P Y, the annual percentage yield, from the bank's own disclosure, recorded with the web address and the date you looked. It's one year of growth, compounding already included.

Type it as four point five, then the percent sign. Excel stores that as zero point zero four five. A plain four point five, no percent sign, means four hundred fifty percent. That one keystroke wrecks the whole model.

B four, the monthly deposit: a hundred fifty dollars. In this model it lands at the end of every month, like saving part of a paycheck. It's fictional classroom money, never your family's real finances.

B five is months, a whole number from zero to sixty. Twenty four for the sample. The table always runs to month sixty; B five just picks which month we report.

Skip to B seven, the down payment target: what you want saved before you buy. Four thousand dollars for the sample, or a percent of your car's out the door price.

Now B six, the monthly equivalent rate. The A P Y says one dollar becomes one point oh four five in a year. We need the one month growth factor that, multiplied by itself twelve times, makes one point oh four five.

Twelve multiplications undo with a twelfth root. In Excel: equals, one plus B three in parentheses, caret, one over twelve in parentheses, minus one. Those parentheses around one twelfth matter, or Excel does the power first.

Press Enter: zero point three six seven four eight percent per month. Check it like the deck does. That monthly factor, to the twelfth power, lands back on one point oh four five.

Here's the trap. A P Y divided by twelve looks reasonable, but divide by twelve is for a nominal rate, the kind a loan contract states. A P Y already includes compounding. Savings: twelfth root. Loan: divide by twelve.


## Chapter 2 · Savings schedule, checks and chart

*About 736 words · 4 min at narration pace.*

Row ten holds the table headers, A through F: Month, Opening balance, Interest, Deposit, Closing balance, Total contributed. Contributions and interest get their own columns, because the whole point is telling them apart.

Row eleven is month zero, the day you open the account. Month: zero. Opening balance: B two, with dollar signs so it stays locked. No interest, no deposit. Closing equals opening. Total contributed starts at B two.

Row twelve is month one, and every later row gets copied from it, so slow down here. Month: A eleven plus one. Opening balance: last month's closing balance, E eleven.

Interest: opening balance times the monthly rate, B twelve times B six. Put dollar signs on B six. When this copies down, B twelve should slide to B thirteen, but the rate has to stay locked.

Deposit: B four, locked with dollar signs. Closing balance: the SUM of B twelve through D twelve, opening plus interest plus deposit. Total contributed: F eleven plus D twelve, only the money you put in.

Notice the order. Interest is figured on the opening balance, before the deposit lands. The deposit arrives at the end of the month, so it earns nothing until month two.

Check by hand before you copy anything. Five hundred times the monthly rate is about a dollar eighty four. Add the hundred fifty deposit. Month one closes at six hundred fifty one dollars and eighty four cents.

Two wrong answers to know. Six fifty two thirty nine means you deposited at the start of the month. Six fifty one eighty eight means you used A P Y divided by twelve. Watch that one happen.

Four cents off in month one: small, but wrong for a reason you can name. Put the twelfth root back. Six fifty one eighty four.

Now copy row twelve down to row seventy one, which is month sixty. Select A twelve through F seventy one and fill down: Control D, or Command D on a Mac.

Month sixty, row seventy one. Every row reads the row above, and the dollar signs kept B four and B six locked. Interest suddenly zero below row twelve? You're missing a dollar sign.

Back up to row eight: the ending balance at month B five. INDEX of E eleven through E seventy one, at position B five plus one. Plus one, because month zero is first in the list.

B nine, the interest earned: B eight minus the total contributed at the same position. INDEX of F eleven through F seventy one, B five plus one. Whatever isn't your own deposits is interest.

Now the published checks. Month twenty four: four thousand three hundred two dollars and thirty three cents. Interest: two hundred two thirty three. So four thousand one hundred came from your deposits. Monday's prediction, answered.

Now the spectacular mistake. Suppose B three holds a plain four point five. Excel reads four hundred fifty percent, and the balance jumps to about forty three thousand eight hundred sixty eight dollars. From a hundred fifty a month? Impossible.

Any answer that big should trigger a reasonableness check. Put the percent sign back, and we're at four thousand three hundred two thirty three again.

Test d, the zero rate test. Set the A P Y to zero. With no interest, the ending balance must equal starting savings plus deposits: five hundred plus twenty four times one fifty. Exactly four thousand one hundred.

If zero percent gives anything else, a formula is making money from nowhere, like adding the deposit twice. Ours passes. Restore four point five percent.

Now the chart: Month against Closing balance and Total contributed, rows eleven to thirty five, through month twenty four. A line chart, axes labeled Months and Dollars, dollar axis starting at zero. Title the finding, not the topic.

The gap between the two lines is the interest. It's thin, and it widens slowly. On a two year horizon, your deposits do almost all the work.

Next, change one assumption at a time and record what you held constant. Test a: find the first month the closing balance reaches your target in B seven, or write not within the horizon.

Test b: change only B three, to two percent. Test c: restore it, then change only B four, to one seventy five. Which matters more? Yours to find. Then restore every base input, because the Loan sheet reads B eight.


## Chapter 3 · Loan sheet: down payment, rate and payment

*About 502 words · 3 min at narration pace.*

Second sheet: Loan. B two, the out the door price: a fifteen thousand dollar car plus a thousand in assumed fees. For your car, make it a formula, listing plus fees, and keep insurance and fuel out of it.

B three, the down payment. Don't retype your savings balance; link it. Equals MIN of B two and Savings B eight. MIN caps the down payment at the price. You can't put down more than the car costs.

Press Enter: four thousand three hundred two thirty three, straight from the Savings sheet. We're assuming the whole balance goes to the car, with no emergency reserve left. Name that in your limitations.

B four, the amount financed: price minus down payment, B two minus B three. Eleven thousand six hundred ninety seven dollars and sixty seven cents. That's the principal, the money you actually borrow.

B five, the annual contract interest rate: seven percent. Label it contract rate on purpose. A lender's A P R can include fees, so it can sit above the rate that drives the payments. With no finance fees, they match.

B six, the term: the number of monthly payments. Sixty for the base case. It has to be a positive whole number. A term of zero isn't a loan; it's an input error.

B seven, the monthly payment. A loan's rate is a nominal annual rate, compounded monthly, so the monthly rate is simply B five divided by twelve. Not the twelfth root this time. Different input, different conversion.

Type: equals IF, B five equals zero, then B four over B six. Otherwise, minus PMT of B five over twelve, B six, B four. That's rate per month, number of payments, and the amount borrowed.

You should see two hundred thirty one dollars sixty three a month. That minus sign matters: Excel reports money you pay out as negative. Skip it, and the payment and the total interest both come out negative.

B eight, total loan interest: payment times term, minus what you borrowed. B seven times B six, minus B four. Two thousand two hundred dollars. Multiply the payment cell, not a rounded number, or you'll be thirteen cents off.

B nine, purchase plus financing cost: the down payment plus every payment. B three plus B seven times B six. Eighteen thousand two hundred dollars, for a sixteen thousand dollar car.

Now the IF earns its place. Set the rate to zero. The textbook formula would divide zero by zero; the IF just splits B four over B six. About a hundred ninety four ninety six, and zero interest.

Put seven percent back. Second edge case: savings bigger than the price. If Savings B two were twenty thousand dollars, the down payment caps at sixteen thousand, and the amount financed is zero.

The extra savings stay in the bank. Set Savings B two back to five hundred, and the payment returns to two thirty one sixty three. Edge cases that behave sensibly are a line on the rubric.


## Chapter 4 · The amortization schedule

*About 384 words · 2 min at narration pace.*

Below the inputs, row eleven gets the amortization headers: Month, Opening balance, Interest, Payment, Principal, Closing balance. Every payment does two jobs: pay this month's interest, then chip away at the balance.

Row twelve is month one. Month: one. Opening balance: B four, locked with dollar signs, the amount financed. Interest: B twelve times B five, divided by twelve. Contract rate over twelve, with B five locked.

Payment: B seven, locked, linked, never typed. Principal: payment minus interest, D twelve minus C twelve. Closing balance: opening minus principal, B twelve minus E twelve.

Check month one. Eleven thousand six ninety seven sixty seven, times seven percent over twelve: sixty eight twenty four of interest. The other hundred sixty three thirty nine pays down principal.

Row thirteen changes two cells. Month: A twelve plus one. Opening balance: the previous closing balance, F twelve. That link is what makes the balance shrink. Then copy C twelve through F twelve down one row.

The most common bug: pointing every opening balance at B four. Then the interest never shrinks, and the loan never pays off. Opening balance always comes from the row above.

Now copy row thirteen down to row seventy one, month sixty. And stop at the term. Rows past the last payment keep subtracting, and the balance goes negative.

Month sixty, row seventy one. Opening balance about two hundred thirty dollars, closing balance zero. In full precision it's a tiny fraction of a cent, so approximately zero is the honest word.

Two more checks, up by the inputs. Final closing balance. The SUM of the principal column, which should equal B four. And the SUM of the interest column, which should equal B eight.

Eleven thousand six ninety seven sixty seven, and two thousand two hundred. Both match: every borrowed dollar paid back, every interest dollar counted. If the final balance is hundreds off, your payment was typed, not linked.

Chart it: interest and principal per payment, by month. A line chart, Months on the horizontal axis, Dollars per payment on the vertical, starting at zero.

Same payment every month; only the split changes. Interest is charged on what you still owe, so as the balance falls, more of each payment reaches principal. Month one: about twenty nine percent interest. Month sixty: under one percent.


## Chapter 5 · 60 vs 72 months, ownership costs, deliverables

*About 599 words · 3 min at narration pace.*

Here's the question that trips everyone. Same car, same down payment, same seven percent. Sixty months, or seventy two with a lower payment. Which loan is cheaper? Careful. Cheaper per month, or cheaper in total?

To keep both terms live, duplicate the Loan sheet. Right click its tab, choose Move or Copy, check Create a copy, and rename the copy Loan seventy two. I'm making that copy now.

On the copy, change exactly one input: B six, to seventy two. Then extend the schedule to row eighty three, month seventy two, and point the three checks at row eighty three.

Seventy two months: a hundred ninety nine forty three a month, two thousand six hundred sixty one fifty five in interest, eighteen thousand six hundred sixty one fifty five in total. Final balance, zero again.

Now a Compare sheet for the scenario table. Columns: Scenario, Changed, Monthly payment, Total loan interest, Purchase plus financing cost. Row three is the base case, sixty months, nothing changed.

Link, don't copy the numbers: equals Loan B seven, Loan B eight, Loan B nine. Row four is seventy two months, changed cell B six, linked to the same three cells on Loan seventy two.

Add a difference row, seventy two minus sixty. Four hundred sixty one dollars fifty five more in interest, and the same amount more in total cost, for about thirty two dollars a month of breathing room.

So the smaller payment is not the cheaper loan. Seventy two months buys monthly relief, and costs four sixty one fifty five more. That trade can be reasonable. Calling it cheaper is the mistake. Always say which cheaper you mean.

Add one more scenario that changes a different single input, like the rate, labeled as an assumption. Rehearse it live: Loan sheet, rate to nine percent, and the base row jumps to two forty two eighty two.

Restore seven percent. Now the costs that don't end when the loan does. Below the table, an Ownership block of monthly estimates, each labeled as a sourced estimate or a classroom assumption.

Insurance: a hundred eighty a month, a classroom assumption. No personal insurance quotes; those need personal information. Next, fuel, because fuel is a formula, not a guess.

Fuel needs three inputs. Miles per month: six hundred. Combined miles per gallon for your exact model, from fuel economy dot gov: thirty for the sample. Price per gallon: three fifty.

Fuel per month: miles divided by miles per gallon, times price per gallon. B eleven over B twelve, times B thirteen. Seventy dollars a month.

Maintenance: fifty a month, labeled. The ownership total is the SUM of insurance, fuel and maintenance. Three hundred dollars a month, on top of any loan payment.

Monthly cash need, payment plus ownership: five thirty one sixty three on sixty months, four ninety nine forty three on seventy two. And to compare total cash out, use the same time span for both loans.

Due Thursday, November twelfth: sources, editable inputs, the savings schedule and chart, the linked loan and amortization schedule, the two term comparison, the ownership block, and a one fifty to two hundred word recommendation.

Use the sentence frame. Saving this much for this many months reaches this balance, and this much of it is interest. That leaves this much to finance, at this rate. Every blank is a cell in your workbook.

Then: I would choose this many months, at this payment and this total interest, versus the other term. With ownership costs, my monthly need is about this much. And one thing that would change your decision.


## Chapter 6 · Ready or Revise

*About 207 words · 1 min at narration pace.*

Before you present, swap with a partner for the Ready or Revise audit. Every Revise needs one specific fix, like: B seven has zero point zero seven typed in, point it at B five.

Mathematical correctness: A P Y root for savings, contract rate over twelve for the loan, end of month deposits, contributions kept separate from interest, the zero rate test passes, and the sample loan is two thirty one sixty three.

Formula structure, tested live. Change Savings B four, the monthly deposit, to two hundred. The ending balance, the down payment and the loan principal should all move.

Down payment five thousand five fifty four forty four. Amount financed ten thousand four forty five fifty six. It moved, so the model is real. Restore the deposit to one fifty.

Research: the car and both accounts have a web address, a date, fees and conditions. Explanation: charts have units and start at zero, scenarios change one input at a time, and the recommendation names total cost and a limit.

So: twelfth root for the A P Y, divide by twelve for the loan, link every cell, and say which cheaper you mean. Build the sample until it matches, then make it yours. See you November twelfth.


## Part D · Sign-off (conversational)

*About 205 words · 1 min at narration pace.*

Looser and warmer than the lesson voice, the way you end a class.

Alright. That is the whole tour. Let me tell you what I actually want you to walk away with.

The spreadsheet is not the point. The physics is not the point. The point is that you can build a small model of the world, check it against one number you computed by hand, and then trust it enough to make a decision with it.

When the model and your hand calculation disagree, the model is not automatically right. Neither are you. Go find the four cents.

When a formula looks intimidating, read it from the inside out. What is in the innermost parentheses? What does that mean? Then one layer out. Then one more.

When a graph looks wrong, look at the axes first. Nine times out of ten, the graph is fine and the axis is lying to you.

And when you are stuck, say so. Out loud, in the room, or in an email at eleven at night. Stuck is a status, not a grade.

Thanks for sticking with this one. It was long. The next one is shorter, I promise. Mostly.

See you Thursday. Bring the deliverable, bring your questions, and bring a charged laptop.

Okay. We are done. Go eat something.
