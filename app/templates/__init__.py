"""
MoneyPrinterTurbo Pro - Content Template System
================================================
Provides pre-built content templates for various niches including
finance, health, tech, education, food, motivation, story, and travel.
Each template includes prompt strategies, visual styles, music recommendations,
and hashtag sets to streamline video content creation.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PromptStrategy:
    """Defines how to generate prompts for a given template."""

    hooks: List[str]
    structures: List[str]
    call_to_actions: List[str]
    tone_keywords: List[str]
    audience_questions: List[str]

    def random_hook(self) -> str:
        return random.choice(self.hooks)

    def random_structure(self) -> str:
        return random.choice(self.structures)

    def random_cta(self) -> str:
        return random.choice(self.call_to_actions)


@dataclass
class VisualStyle:
    """Visual styling parameters for generated videos."""

    color_palette: List[str]
    font_style: str
    transition_type: str
    overlay_effects: List[str]
    thumbnail_style: str
    aspect_ratio: str = "9:16"

    def describe(self) -> str:
        colors = ", ".join(self.color_palette)
        return (
            f"Colors: {colors} | Font: {self.font_style} | "
            f"Transitions: {self.transition_type} | Aspect: {self.aspect_ratio}"
        )


@dataclass
class MusicStyle:
    """Music and audio styling for videos."""

    genre: str
    bpm_range: tuple
    mood: str
    instrument_keywords: List[str]
    volume_level: str = "background"

    def describe(self) -> str:
        instruments = ", ".join(self.instrument_keywords)
        return (
            f"{self.genre} | BPM {self.bpm_range[0]}-{self.bpm_range[1]} | "
            f"Mood: {self.mood} | Instruments: {instruments}"
        )


@dataclass
class ContentTemplate:
    """A complete content template for a specific niche."""

    id: str
    name: str
    description: str
    icon: str
    prompt_strategy: PromptStrategy
    visual_style: VisualStyle
    music_style: MusicStyle
    hashtags: List[str]
    target_duration_seconds: int = 60
    platforms: List[str] = field(default_factory=lambda: ["tiktok", "youtube_shorts", "instagram_reels"])

    def generate_prompt(self, topic: str, extra_context: str = "") -> Dict[str, Any]:
        """Generate a full content prompt from this template for a given topic."""
        hook = self.prompt_strategy.random_hook()
        structure = self.prompt_strategy.random_structure()
        cta = self.prompt_strategy.random_cta()
        tone = random.choice(self.prompt_strategy.tone_keywords)
        question = random.choice(self.prompt_strategy.audience_questions)
        hashtags = " ".join(random.sample(self.hashtags, min(5, len(self.hashtags))))

        script_prompt = (
            f"{hook}\n\n"
            f"Topic: {topic}\n"
            f"Tone: {tone}\n"
            f"Structure: {structure}\n"
            f"Engagement question: {question}\n"
            f"Call to action: {cta}\n"
        )
        if extra_context:
            script_prompt += f"Additional context: {extra_context}\n"

        return {
            "template_id": self.id,
            "template_name": self.name,
            "script_prompt": script_prompt,
            "visual_style": self.visual_style.describe(),
            "music_style": self.music_style.describe(),
            "hashtags": hashtags,
            "target_duration": self.target_duration_seconds,
            "platforms": self.platforms,
            "tone": tone,
            "color_palette": self.visual_style.color_palette,
            "font_style": self.visual_style.font_style,
            "transition_type": self.visual_style.transition_type,
            "thumbnail_style": self.visual_style.thumbnail_style,
            "music_genre": self.music_style.genre,
            "music_mood": self.music_style.mood,
        }

    def generate_outline(self, topic: str, num_scenes: int = 5) -> List[Dict[str, str]]:
        """Generate a scene-by-scene outline for the video."""
        structure = self.prompt_strategy.random_structure()
        scenes = []
        for i in range(1, num_scenes + 1):
            if i == 1:
                scene_type = "hook"
                note = f"Grab attention immediately with: {self.prompt_strategy.random_hook()}"
            elif i == num_scenes:
                scene_type = "outro"
                note = f"Close with: {self.prompt_strategy.random_cta()}"
            elif i == num_scenes - 1:
                scene_type = "climax"
                note = "Deliver the most impactful information or emotional peak"
            else:
                scene_type = "body"
                note = f"Develop the topic: {topic}"
            scenes.append({
                "scene_number": i,
                "type": scene_type,
                "note": note,
                "suggested_duration": f"{self.target_duration_seconds // num_scenes}s",
            })
        return scenes


# ---------------------------------------------------------------------------
# Template Definitions
# ---------------------------------------------------------------------------

def _build_finance_template() -> ContentTemplate:
    return ContentTemplate(
        id="finance",
        name="Finance & Money",
        description="Personal finance tips, investing advice, money-saving hacks, and financial literacy content.",
        icon="💰",
        prompt_strategy=PromptStrategy(
            hooks=[
                "💰 This money habit changed my life...",
                "Stop losing money! Here's what the rich know...",
                "99% of people don't know this about investing...",
                "If you're broke, watch this NOW.",
                "I turned $100 into $10,000 — here's how.",
                "The #1 financial mistake you're making right now.",
            ],
            structures=[
                "Problem → Explanation → Solution → Action Step",
                "Myth → Truth → Proof → Next Steps",
                "Numbered tips (5 quick finance hacks)",
                "Before & After financial transformation",
                "Storytelling: relatable money struggle → breakthrough",
            ],
            call_to_actions=[
                "Follow for daily money tips! 💸",
                "Save this for later — you'll need it!",
                "Drop a 💰 if you're ready to level up your finances!",
                "Share this with someone who needs to hear it!",
                "Comment your biggest money goal below!",
            ],
            tone_keywords=["authoritative", "approachable", "urgent", "motivational", "educational"],
            audience_questions=[
                "What's your biggest money struggle?",
                "How much do you save each month?",
                "Are you investing yet? Why or why not?",
                "What would you do with an extra $1000?",
            ],
        ),
        visual_style=VisualStyle(
            color_palette=["#0D1B2A", "#1B2838", "#00C896", "#FFD700", "#FFFFFF"],
            font_style="bold sans-serif with financial iconography",
            transition_type="smooth swipe with number animations",
            overlay_effects=["stock ticker overlay", "money counter animation", "green/red arrows"],
            thumbnail_style="bold text on dark gradient with money symbols",
        ),
        music_style=MusicStyle(
            genre="lo-fi hip hop / corporate upbeat",
            bpm_range=(90, 120),
            mood="confident and focused",
            instrument_keywords=["soft piano", "muted guitar", "subtle bass", "clean drums"],
        ),
        hashtags=[
            "#MoneyTips", "#FinanceTok", "#Investing", "#WealthBuilding",
            "#PersonalFinance", "#MoneyMindset", "#FinancialFreedom",
            "#BudgetingTips", "#PassiveIncome", "#MoneyHacks",
            "#StockMarket", "#CryptoTips", "#SavingMoney", "#DebtFree",
            "#SideHustle",
        ],
        target_duration_seconds=60,
    )


def _build_health_template() -> ContentTemplate:
    return ContentTemplate(
        id="health",
        name="Health & Wellness",
        description="Fitness routines, nutrition tips, mental health awareness, and holistic wellness content.",
        icon="🏋️",
        prompt_strategy=PromptStrategy(
            hooks=[
                "This 30-second habit will change your health forever...",
                "Your doctor wishes you knew this sooner.",
                "I tried this for 30 days — the results shocked me.",
                "Stop eating this immediately! Here's why...",
                "The truth about [health topic] nobody talks about.",
                "POV: You finally started taking care of yourself.",
            ],
            structures=[
                "Myth → Science → Simple Tip → Transformation promise",
                "Day 1 vs Day 30 challenge format",
                "Quick routine: Step 1 → Step 2 → Step 3 → Result",
                "Problem (symptoms) → Root cause → Natural solution",
                "Before/After with scientific explanation",
            ],
            call_to_actions=[
                "Save this for your next workout! 💪",
                "Tag someone who needs this health tip!",
                "Follow for daily wellness content! 🌿",
                "Try this for 7 days and tell me how you feel!",
                "Drop a 🏋️ if you're prioritizing your health!",
            ],
            tone_keywords=["energetic", "empathetic", "scientific", "encouraging", "reassuring"],
            audience_questions=[
                "What's your biggest health goal right now?",
                "How many hours do you sleep each night?",
                "Do you drink enough water daily?",
                "What's stopping you from working out?",
            ],
        ),
        visual_style=VisualStyle(
            color_palette=["#FFFFFF", "#E8F5E9", "#4CAF50", "#FF5722", "#2196F3"],
            font_style="clean modern sans-serif with fitness icons",
            transition_type="energetic cuts with timer overlays",
            overlay_effects=["rep counter", "calorie tracker", "heart rate animation", "progress bar"],
            thumbnail_style="split before/after or energetic pose with bold text",
        ),
        music_style=MusicStyle(
            genre="upbeat pop / workout EDM",
            bpm_range=(120, 150),
            mood="energetic and motivating",
            instrument_keywords=["driving bass", "electronic synths", "powerful drums", "uplifting melody"],
        ),
        hashtags=[
            "#HealthTips", "#FitnessTok", "#Wellness", "#Nutrition",
            "#WorkoutMotivation", "#HealthyLifestyle", "#MentalHealth",
            "#CleanEating", "#FitnessJourney", "#SelfCare",
            "#GymLife", "#MealPrep", "#Mindfulness", "#Yoga",
            "#WeightLoss",
        ],
        target_duration_seconds=45,
    )


def _build_tech_template() -> ContentTemplate:
    return ContentTemplate(
        id="tech",
        name="Technology & AI",
        description="Tech reviews, AI tutorials, gadget unboxings, coding tips, and digital trend explainers.",
        icon="🤖",
        prompt_strategy=PromptStrategy(
            hooks=[
                "This AI tool will replace your entire workflow...",
                "I tested the latest [gadget] — here's the truth.",
                "You're using your phone wrong. Let me show you.",
                "In 2026, this tech changes everything.",
                "The app nobody is talking about — but should be.",
                "Coder secret: This one trick saves hours of work.",
            ],
            structures=[
                "Problem → Tool reveal → Demo → Verdict",
                "Top 5 countdown with quick demos",
                "Deep dive: Feature 1 → Feature 2 → Pros/Cons → Rating",
                "Tutorial: Step-by-step walkthrough",
                "Hot take: Bold claim → Evidence → Community poll",
            ],
            call_to_actions=[
                "Follow for more tech tips! ⚡",
                "Save this — you'll thank me later!",
                "Comment 'LINK' and I'll send you the tool!",
                "Which gadget should I review next?",
                "Share this with your tech-obsessed friend!",
            ],
            tone_keywords=["knowledgeable", "excited", "honest", "analytical", "futuristic"],
            audience_questions=[
                "Are you team Apple or Android?",
                "What's the best tech purchase you've made?",
                "How many hours a day do you spend on screens?",
                "What tech problem frustrates you most?",
            ],
        ),
        visual_style=VisualStyle(
            color_palette=["#0F0F0F", "#1A1A2E", "#00D4FF", "#7B2FFF", "#E0E0E0"],
            font_style="monospace accents with sleek tech typography",
            transition_type="glitch effects and smooth zooms",
            overlay_effects=["code snippets", "spec comparisons", "loading animations", "HUD overlay"],
            thumbnail_style="dark background with neon glow and product image",
        ),
        music_style=MusicStyle(
            genre="synthwave / electronic ambient",
            bpm_range=(100, 130),
            mood="futuristic and curious",
            instrument_keywords=["synth pads", "digital arpeggios", "sub bass", "glitch effects"],
        ),
        hashtags=[
            "#TechTok", "#AI", "#TechReview", "#Coding",
            "#Programming", "#Gadgets", "#TechTips", "#FutureTech",
            "#AppReview", "#TechNews", "#MachineLearning", "#Python",
            "#Unboxing", "#SmartHome", "#CyberSecurity",
        ],
        target_duration_seconds=60,
    )


def _build_education_template() -> ContentTemplate:
    return ContentTemplate(
        id="education",
        name="Education & Learning",
        description="Study tips, science explainers, history facts, language learning, and knowledge-sharing content.",
        icon="📚",
        prompt_strategy=PromptStrategy(
            hooks=[
                "Everything you learned about [topic] is wrong...",
                "In 60 seconds, I'll teach you something mind-blowing.",
                "Here's what schools should teach but don't.",
                "The simplest explanation of [complex topic] you'll ever hear.",
                "Fun fact that will make you the smartest person in the room.",
                "You won't believe this actually happened in history.",
            ],
            structures=[
                "Question → Explanation → Visual proof → Fun twist",
                "Did you know? → Deep dive → Quick quiz → Reveal",
                "Timeline: Origin → Development → Modern day → Future",
                "ELI5 (Explain Like I'm 5) format with analogies",
                "Top 3 misconceptions debunked with evidence",
            ],
            call_to_actions=[
                "Follow to learn something new every day! 🧠",
                "Save this for your next trivia night!",
                "Share this with someone who loves learning!",
                "Comment a topic you want me to explain next!",
                "Drop a 📚 if you learned something today!",
            ],
            tone_keywords=["curious", "clear", "witty", "inspiring", "accessible"],
            audience_questions=[
                "Did you already know this?",
                "What topic should I explain next?",
                "What's the most interesting fact you know?",
                "Did this blow your mind?",
            ],
        ),
        visual_style=VisualStyle(
            color_palette=["#FFFBF0", "#FFD166", "#06D6A0", "#118AB2", "#073B4C"],
            font_style="handwritten chalkboard mixed with modern text",
            transition_type="whiteboard animations and text reveals",
            overlay_effects=["diagrams", "timelines", "bullet point highlights", "quiz popups"],
            thumbnail_style="intriguing question text with related imagery",
        ),
        music_style=MusicStyle(
            genre="light acoustic / soft piano",
            bpm_range=(80, 110),
            mood="curious and light",
            instrument_keywords=["ukulele", "pizzicato strings", "xylophone", "soft percussion"],
        ),
        hashtags=[
            "#LearnOnTikTok", "#Education", "#FunFacts", "#ScienceTok",
            "#HistoryTok", "#StudyTips", "#KnowledgeIsPower", "#DidYouKnow",
            "#MindBlown", "#StudyGram", "#LanguageLearning", "#Biology",
            "#Physics", "#MathTok", "#Philosophy",
        ],
        target_duration_seconds=60,
    )


def _build_food_template() -> ContentTemplate:
    return ContentTemplate(
        id="food",
        name="Food & Recipes",
        description="Quick recipes, food reviews, cooking hacks, restaurant guides, and culinary culture content.",
        icon="🍳",
        prompt_strategy=PromptStrategy(
            hooks=[
                "This 5-minute recipe changed my dinner game forever...",
                "POV: You finally learned to cook like a chef.",
                "The secret ingredient restaurants don't want you to know.",
                "I ate at the #1 rated restaurant — was it worth it?",
                "Making [dish] from scratch — you won't believe how easy it is.",
                "Food hack that saves time AND money.",
            ],
            structures=[
                "Ingredients list → Step-by-step cooking → Final reveal → Taste reaction",
                "Quick recipe: 3 ingredients, 5 minutes, 1 amazing dish",
                "Food review: Presentation → First bite → Verdict → Rating",
                "Cooking challenge or dupe: Restaurant vs homemade",
                "Cultural food journey: History → Recipe → Taste experience",
            ],
            call_to_actions=[
                "Save this recipe for later! 🍽️",
                "Tag someone you'd cook this for!",
                "Follow for easy recipes every day! 👨‍🍳",
                "Rate this dish 1-10 in the comments!",
                "What recipe should I try next?",
            ],
            tone_keywords=["warm", "enthusiastic", "sensory", "fun", "inviting"],
            audience_questions=[
                "What's your comfort food?",
                "Would you try this recipe?",
                "Home cooking or eating out?",
                "What's the best dish you've ever made?",
            ],
        ),
        visual_style=VisualStyle(
            color_palette=["#FFF8F0", "#FF6B35", "#F7C59F", "#2E4057", "#004E64"],
            font_style="playful rounded fonts with food icons",
            transition_type="smooth overhead shots and close-up zooms",
            overlay_effects=["ingredient popups", "timer countdowns", "steam/smoke effects", "recipe cards"],
            thumbnail_style="close-up food shot with recipe name in bold",
        ),
        music_style=MusicStyle(
            genre="acoustic guitar / feel-good indie pop",
            bpm_range=(100, 125),
            mood="warm and cozy",
            instrument_keywords=["acoustic guitar", "whistle melody", "claps", "light percussion"],
        ),
        hashtags=[
            "#FoodTok", "#Recipe", "#EasyRecipes", "#Cooking",
            "#FoodReview", "#HomeCooking", "#FoodHacks", "#MealPrep",
            "#ComfortFood", "#ChefLife", "#Baking", "#HealthyEating",
            "#Foodie", "#StreetFood", "#ViralRecipes",
        ],
        target_duration_seconds=45,
    )


def _build_motivation_template() -> ContentTemplate:
    return ContentTemplate(
        id="motivation",
        name="Motivation & Mindset",
        description="Inspirational speeches, productivity tips, success mindset, goal-setting, and personal growth content.",
        icon="🔥",
        prompt_strategy=PromptStrategy(
            hooks=[
                "Stop scrolling. You need to hear this today.",
                "The difference between successful people and everyone else...",
                "You're not lazy — you're just doing it wrong.",
                "This mindset shift will change your entire life.",
                "If you're feeling stuck, watch this right now.",
                "One year from now, you'll wish you started today.",
            ],
            structures=[
                "Pain point → Reframe → Action plan → Empowerment close",
                "Quote → Story → Lesson → Challenge to viewer",
                "3 harsh truths that will set you free",
                "Daily routine of successful people",
                "Overcoming failure: Story → Lesson → New beginning",
            ],
            call_to_actions=[
                "Share this with someone who needs it! 🔥",
                "Follow for daily motivation! 💪",
                "Screenshot this and make it your wallpaper!",
                "Comment 'I'M IN' if you're ready to change!",
                "Save this for when you need a reminder!",
            ],
            tone_keywords=["passionate", "direct", "empathetic", "powerful", "raw"],
            audience_questions=[
                "What's holding you back right now?",
                "What's your biggest goal this year?",
                "When was the last time you pushed past your comfort zone?",
                "What would you do if you couldn't fail?",
            ],
        ),
        visual_style=VisualStyle(
            color_palette=["#0A0A0A", "#1A1A1A", "#FF4500", "#FFD700", "#FFFFFF"],
            font_style="heavy bold condensed typography",
            transition_type="cinematic slow motion cuts and text slams",
            overlay_effects=["dramatic text reveals", "dark vignette", "film grain", "particle effects"],
            thumbnail_style="dark cinematic background with bold white/red motivational text",
        ),
        music_style=MusicStyle(
            genre="cinematic orchestral / epic motivational",
            bpm_range=(70, 100),
            mood="powerful and inspiring",
            instrument_keywords=["strings ensemble", "epic drums", "piano crescendo", "choir pads"],
        ),
        hashtags=[
            "#Motivation", "#Mindset", "#SuccessMindset", "#DailyMotivation",
            "#HustleCulture", "#GoalSetting", "#PersonalGrowth",
            "#MotivationalSpeech", "#NeverGiveUp", "#BelieveInYourself",
            "#MentalStrength", "#Discipline", "#SelfImprovement",
            "#Entrepreneur", "#MillionaireMindset",
        ],
        target_duration_seconds=60,
    )


def _build_story_template() -> ContentTemplate:
    return ContentTemplate(
        id="story",
        name="Story & Narration",
        description="Reddit stories, creative fiction, true crime, personal anecdotes, and narrative-driven content.",
        icon="📖",
        prompt_strategy=PromptStrategy(
            hooks=[
                "You won't believe what happened next...",
                "This is the craziest story I've ever heard.",
                "I need to tell you about the weirdest thing that happened to me.",
                "This story has a twist ending you'll never see coming.",
                "True story: this changed everything I believed.",
                "So I found out something I was never supposed to know...",
            ],
            structures=[
                "Setup → Rising tension → Climax → Twist → Resolution",
                "Mystery hook → Clues revealed → Big reveal → Aftermath",
                "Dialogue-heavy narrative with scene descriptions",
                "First-person confession style with emotional peaks",
                "Timeline: Day 1 → Escalation → Breaking point → Conclusion",
            ],
            call_to_actions=[
                "Part 2? Comment if you want the rest! 📖",
                "Follow for more stories! 🔔",
                "What would YOU have done? Comment below!",
                "Share this with someone who loves crazy stories!",
                "Save this — the ending is worth it!",
            ],
            tone_keywords=["dramatic", "suspenseful", "emotional", "conversational", "mysterious"],
            audience_questions=[
                "Has something like this ever happened to you?",
                "Did you see the twist coming?",
                "What would you do in this situation?",
                "Want a Part 2?",
            ],
        ),
        visual_style=VisualStyle(
            color_palette=["#1A1A2E", "#16213E", "#E94560", "#0F3460", "#F5F5DC"],
            font_style="serif typewriter with handwritten accents",
            transition_type="slow cinematic pans and fade transitions",
            overlay_effects=["subtitles with emphasis", "dramatic lighting shifts", "chapter cards", "particle dust"],
            thumbnail_style="mysterious imagery with dramatic text overlay and question mark",
        ),
        music_style=MusicStyle(
            genre="ambient cinematic / dark atmospheric",
            bpm_range=(60, 90),
            mood="suspenseful and immersive",
            instrument_keywords=["dark piano", "low strings", "ambient drones", "tension risers"],
        ),
        hashtags=[
            "#StoryTime", "#RedditStories", "#TrueCrime", "#StoryTok",
            "#ToldYouSo", "#Narration", "#CreativeWriting", "#PlotTwist",
            "#HorrorStories", "#Confessions", "#Drama", "#Suspense",
            "#TrueStory", "#MysteryTok", "#ViralStory",
        ],
        target_duration_seconds=90,
    )


def _build_travel_template() -> ContentTemplate:
    return ContentTemplate(
        id="travel",
        name="Travel & Adventure",
        description="Travel guides, destination showcases, budget travel tips, cultural experiences, and adventure content.",
        icon="✈️",
        prompt_strategy=PromptStrategy(
            hooks=[
                "This hidden gem destination costs less than $50/day...",
                "I found paradise — and almost nobody knows about it.",
                "Don't visit [place] until you watch this.",
                "The most underrated travel destination in the world.",
                "I quit my job to travel — here's what happened.",
                "You can travel the world on $30/day. Here's proof.",
            ],
            structures=[
                "Stunning reveal → Hidden info → Cost breakdown → Travel tips",
                "Top 5 countdown: destinations, tips, or mistakes to avoid",
                "Vlog-style: Arrival → Exploration → Food → Culture → Final thoughts",
                "Budget breakdown: Flights → Accommodation → Food → Activities",
                "Day-by-day itinerary with insider tips",
            ],
            call_to_actions=[
                "Save this for your next trip! ✈️",
                "Tag your travel buddy! 🌍",
                "Follow for hidden gem destinations!",
                "Where should I travel next? Comment below!",
                "Share this with someone planning a trip!",
            ],
            tone_keywords=["adventurous", "awe-inspired", "practical", "warm", "wanderlust"],
            audience_questions=[
                "Where's your dream destination?",
                "Are you a budget or luxury traveler?",
                "What's the best place you've ever visited?",
                "Beach vacation or mountain adventure?",
            ],
        ),
        visual_style=VisualStyle(
            color_palette=["#87CEEB", "#FF6F61", "#FFD700", "#2E8B57", "#FFFFFF"],
            font_style="handwritten travel journal with map accents",
            transition_type="smooth aerial shots and immersive first-person transitions",
            overlay_effects=["location pins", "price tags", "map animations", "flag emojis"],
            thumbnail_style="stunning landscape with destination name in stylish font",
        ),
        music_style=MusicStyle(
            genre="tropical house / acoustic world music",
            bpm_range=(105, 128),
            mood="uplifting and adventurous",
            instrument_keywords=["steel drums", "ukulele", "marimba", "light acoustic guitar"],
        ),
        hashtags=[
            "#TravelTok", "#Wanderlust", "#TravelGuide", "#HiddenGem",
            "#BudgetTravel", "#TravelTips", "#Backpacking", "#DigitalNomad",
            "#TravelTheWorld", "#ExploreMore", "#SoloTravel",
            "#TravelHacks", "#DestinationGuide", "#Adventure",
            "#CulturalExperience",
        ],
        target_duration_seconds=60,
    )


# ---------------------------------------------------------------------------
# Template Manager
# ---------------------------------------------------------------------------

class TemplateManager:
    """
    Central manager for all content templates.

    Provides methods to list, retrieve, search, and generate content
    from the built-in template library.
    """

    def __init__(self) -> None:
        self._templates: Dict[str, ContentTemplate] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register all built-in templates."""
        builders = [
            _build_finance_template,
            _build_health_template,
            _build_tech_template,
            _build_education_template,
            _build_food_template,
            _build_motivation_template,
            _build_story_template,
            _build_travel_template,
        ]
        for builder in builders:
            template = builder()
            self._templates[template.id] = template

    # -- Public API -----------------------------------------------------------

    def list_templates(self) -> List[Dict[str, str]]:
        """Return a summary list of all available templates."""
        return [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "icon": t.icon,
            }
            for t in self._templates.values()
        ]

    def get_template(self, template_id: str) -> Optional[ContentTemplate]:
        """Retrieve a template by its unique id."""
        return self._templates.get(template_id)

    def search_templates(self, keyword: str) -> List[ContentTemplate]:
        """Search templates by keyword in name, description, or hashtags."""
        keyword_lower = keyword.lower()
        results = []
        for t in self._templates.values():
            searchable = (
                f"{t.name} {t.description} {' '.join(t.hashtags)}".lower()
            )
            if keyword_lower in searchable:
                results.append(t)
        return results

    def generate_prompt(
        self,
        template_id: str,
        topic: str,
        extra_context: str = "",
    ) -> Dict[str, Any]:
        """
        Generate a full content prompt for a given template and topic.

        Returns a dictionary with script_prompt, visual_style, music_style,
        hashtags, and all necessary parameters for video generation.

        Raises:
            KeyError: If template_id is not found.
        """
        template = self.get_template(template_id)
        if template is None:
            available = ", ".join(self._templates.keys())
            raise KeyError(
                f"Template '{template_id}' not found. Available: {available}"
            )
        return template.generate_prompt(topic, extra_context)

    def generate_outline(
        self,
        template_id: str,
        topic: str,
        num_scenes: int = 5,
    ) -> List[Dict[str, str]]:
        """Generate a scene outline for a video using the specified template."""
        template = self.get_template(template_id)
        if template is None:
            available = ", ".join(self._templates.keys())
            raise KeyError(
                f"Template '{template_id}' not found. Available: {available}"
            )
        return template.generate_outline(topic, num_scenes)

    def generate_multi_platform(
        self,
        template_id: str,
        topic: str,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Generate platform-specific prompt variants.

        Adjusts duration and style hints per platform (tiktok, youtube_shorts,
        instagram_reels).
        """
        base = self.generate_prompt(template_id, topic)
        platforms = {
            "tiktok": {"max_duration": 60, "style_note": "Fast-paced, trend-aware, vertical"},
            "youtube_shorts": {"max_duration": 60, "style_note": "Slightly longer hooks, searchable title"},
            "instagram_reels": {"max_duration": 90, "style_note": "Aesthetic-focused, shareable, caption-friendly"},
        }
        result = {}
        for platform, config in platforms.items():
            variant = dict(base)
            variant["platform"] = platform
            variant["target_duration"] = min(base["target_duration"], config["max_duration"])
            variant["platform_style_note"] = config["style_note"]
            result[platform] = variant
        return result

    def get_random_template(self) -> ContentTemplate:
        """Return a random template — useful for content inspiration."""
        return random.choice(list(self._templates.values()))

    @property
    def template_count(self) -> int:
        """Number of registered templates."""
        return len(self._templates)

    def __len__(self) -> int:
        return len(self._templates)

    def __contains__(self, template_id: str) -> bool:
        return template_id in self._templates

    def __repr__(self) -> str:
        return f"TemplateManager(templates={self.template_count})"


# ---------------------------------------------------------------------------
# Module-level convenience instance
# ---------------------------------------------------------------------------

_manager: Optional[TemplateManager] = None


def get_template_manager() -> TemplateManager:
    """Get or create the singleton TemplateManager instance."""
    global _manager
    if _manager is None:
        _manager = TemplateManager()
    return _manager
