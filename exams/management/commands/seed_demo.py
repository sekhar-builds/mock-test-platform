"""Load sample subjects, tests and a demo student account.

Safe to run on every deploy: existing tests are left untouched, so edits made
in the admin are never overwritten.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from exams.models import Choice, Question, Subject, Test

DEMO_USERNAME = "demo"
DEMO_PASSWORD = "demo12345"

# Each question: (text, [options], index of correct option, explanation)
TESTS = [
    {
        "subject": "Modern Indian History",
        "title": "Freedom Struggle: 1885 to 1947",
        "slug": "freedom-struggle-1885-1947",
        "description": "Key events, leaders and turning points of the Indian national movement, from the founding of the Congress to Independence.",
        "duration": 10,
        "marks": 2,
        "negative": "0.66",
        "questions": [
            ("Who presided over the first session of the Indian National Congress?",
             ["Dadabhai Naoroji", "W. C. Bonnerjee", "Surendranath Banerjee", "A. O. Hume"], 1,
             "The first session was held in Bombay in December 1885 and was presided over by W. C. Bonnerjee. A. O. Hume, a retired civil servant, played a key role in founding the Congress."),
            ("The Partition of Bengal (1905) was carried out during the tenure of which Viceroy?",
             ["Lord Ripon", "Lord Curzon", "Lord Minto", "Lord Dalhousie"], 1,
             "Lord Curzon announced the partition in 1905. It triggered the Swadeshi Movement and was annulled in 1911 under Lord Hardinge."),
            ("In which year did the Jallianwala Bagh massacre take place?",
             ["1915", "1919", "1922", "1930"], 1,
             "On 13 April 1919, troops under General Dyer fired on a peaceful gathering at Jallianwala Bagh in Amritsar."),
            ("From where did Gandhi begin the Dandi March?",
             ["Sabarmati Ashram", "Sevagram, Wardha", "Champaran", "Bardoli"], 0,
             "Gandhi set out from Sabarmati Ashram on 12 March 1930 and reached Dandi on 6 April, breaking the salt law and launching the Civil Disobedience Movement."),
            ("Which leader gave the call 'Do or Die'?",
             ["Jawaharlal Nehru", "Subhas Chandra Bose", "Mahatma Gandhi", "Bal Gangadhar Tilak"], 2,
             "Gandhi gave the 'Do or Die' call in August 1942 at the launch of the Quit India Movement."),
            ("The Non-Cooperation Movement was called off after which incident?",
             ["Chauri Chaura", "Kakori train action", "Moplah uprising", "Jallianwala Bagh"], 0,
             "After a mob set fire to a police station at Chauri Chaura (Gorakhpur) in February 1922, Gandhi withdrew the movement because it had turned violent."),
            ("Who founded the Servants of India Society in 1905?",
             ["Bal Gangadhar Tilak", "Gopal Krishna Gokhale", "M. G. Ranade", "Dadabhai Naoroji"], 1,
             "Gopal Krishna Gokhale founded the Servants of India Society in Pune to train dedicated workers for public service."),
            ("The 'Purna Swaraj' resolution was adopted at which session of the Congress?",
             ["Lucknow, 1916", "Lahore, 1929", "Karachi, 1931", "Haripura, 1938"], 1,
             "The Lahore session of December 1929, presided over by Jawaharlal Nehru, declared complete independence as the goal."),
            ("In which year did the Cabinet Mission arrive in India?",
             ["1942", "1945", "1946", "1947"], 2,
             "The Cabinet Mission of Pethick-Lawrence, Stafford Cripps and A. V. Alexander arrived in March 1946 to plan the transfer of power."),
            ("Who led the Bardoli Satyagraha of 1928?",
             ["Vallabhbhai Patel", "Rajendra Prasad", "C. Rajagopalachari", "Motilal Nehru"], 0,
             "Vallabhbhai Patel led the peasants of Bardoli against an increase in land revenue; the women of Bardoli gave him the title 'Sardar'."),
        ],
    },
    {
        "subject": "Indian Polity",
        "title": "Constitution Basics",
        "slug": "constitution-basics",
        "description": "Core facts about the making of the Constitution, Fundamental Rights, Duties and key constitutional offices.",
        "duration": 8,
        "marks": 1,
        "negative": "0",
        "questions": [
            ("On which date was the Constitution of India adopted by the Constituent Assembly?",
             ["15 August 1947", "26 November 1949", "26 January 1950", "26 January 1949"], 1,
             "The Constitution was adopted on 26 November 1949 (now observed as Constitution Day) and came into force on 26 January 1950."),
            ("Who was the Chairman of the Drafting Committee of the Constituent Assembly?",
             ["Rajendra Prasad", "B. R. Ambedkar", "Jawaharlal Nehru", "B. N. Rau"], 1,
             "Dr B. R. Ambedkar chaired the Drafting Committee. Dr Rajendra Prasad was President of the Constituent Assembly, and B. N. Rau was its constitutional adviser."),
            ("Fundamental Rights are contained in which Part of the Constitution?",
             ["Part II", "Part III", "Part IV", "Part IV-A"], 1,
             "Part III (Articles 12 to 35) contains the Fundamental Rights. Part IV covers the Directive Principles and Part IV-A the Fundamental Duties."),
            ("Article 21 of the Constitution guarantees:",
             ["Equality before law", "Protection of life and personal liberty", "Freedom of speech", "Right to constitutional remedies"], 1,
             "Article 21 says no person shall be deprived of life or personal liberty except according to procedure established by law."),
            ("Fundamental Duties were added to the Constitution by which amendment?",
             ["24th Amendment", "42nd Amendment", "44th Amendment", "73rd Amendment"], 1,
             "The 42nd Amendment (1976), based on the Swaran Singh Committee's recommendations, inserted Part IV-A with the Fundamental Duties."),
            ("The Right to Property ceased to be a Fundamental Right through which amendment?",
             ["42nd Amendment", "44th Amendment", "52nd Amendment", "86th Amendment"], 1,
             "The 44th Amendment (1978) removed it from Part III. It is now a constitutional right under Article 300A."),
            ("Who appoints the Chief Justice of India?",
             ["The Prime Minister", "The President", "The Parliament", "The Law Minister"], 1,
             "Under Article 124, judges of the Supreme Court, including the Chief Justice, are appointed by the President."),
            ("What is the minimum age to become a member of the Lok Sabha?",
             ["18 years", "21 years", "25 years", "30 years"], 2,
             "A candidate must be at least 25 years old for the Lok Sabha and at least 30 for the Rajya Sabha."),
        ],
    },
    {
        "subject": "Geography",
        "title": "Physical Geography of India",
        "slug": "physical-geography-india",
        "description": "Rivers, mountains, coastlines and soils of India: a quick revision set for competitive exams.",
        "duration": 10,
        "marks": 1,
        "negative": "0.25",
        "questions": [
            ("Which is the longest river of peninsular India?",
             ["Krishna", "Godavari", "Narmada", "Mahanadi"], 1,
             "The Godavari, often called the 'Dakshin Ganga', is the longest peninsular river. It rises at Trimbakeshwar in Maharashtra."),
            ("Which river flows westward through a rift valley into the Arabian Sea?",
             ["Godavari", "Krishna", "Narmada", "Kaveri"], 2,
             "The Narmada flows west between the Vindhya and Satpura ranges through a rift valley and forms an estuary before entering the Arabian Sea."),
            ("Which is the highest peak of the Western Ghats?",
             ["Doddabetta", "Anamudi", "Mahendragiri", "Guru Shikhar"], 1,
             "Anamudi (about 2,695 m) in Kerala is the highest peak of the Western Ghats and of South India. Doddabetta is the highest in the Nilgiris."),
            ("The Tropic of Cancer does NOT pass through which of these states?",
             ["Gujarat", "Rajasthan", "Odisha", "Madhya Pradesh"], 2,
             "The Tropic of Cancer passes through eight states: Gujarat, Rajasthan, Madhya Pradesh, Chhattisgarh, Jharkhand, West Bengal, Tripura and Mizoram. Odisha lies to its south."),
            ("The Palk Strait separates India from which country?",
             ["Maldives", "Sri Lanka", "Myanmar", "Bangladesh"], 1,
             "The Palk Strait lies between Tamil Nadu and the northern tip of Sri Lanka."),
            ("Which state has the longest coastline in India?",
             ["Gujarat", "Andhra Pradesh", "Tamil Nadu", "Maharashtra"], 0,
             "Gujarat has the longest coastline of any Indian state, thanks to the Gulf of Kutch and the Gulf of Khambhat."),
            ("Majuli, one of the largest river islands in the world, lies in which river?",
             ["Ganga", "Brahmaputra", "Godavari", "Mahanadi"], 1,
             "Majuli lies in the Brahmaputra in Assam and is known for its Vaishnavite satras."),
            ("Black soil of the Deccan plateau is also known as:",
             ["Laterite soil", "Regur soil", "Alluvial soil", "Peaty soil"], 1,
             "Black soil is called regur. It retains moisture well and is ideal for cotton, which is why it is also called black cotton soil."),
        ],
    },
    {
        "subject": "General Science",
        "title": "Everyday Science",
        "slug": "everyday-science",
        "description": "Basic physics, chemistry and biology questions that appear regularly in state PSC, SSC and banking exams.",
        "duration": 8,
        "marks": 1,
        "negative": "0",
        "questions": [
            ("What is the chemical formula of common salt?",
             ["KCl", "NaCl", "NaHCO3", "CaCO3"], 1,
             "Common salt is sodium chloride (NaCl). NaHCO3 is baking soda and CaCO3 is limestone."),
            ("Which vitamin does the human skin produce when exposed to sunlight?",
             ["Vitamin A", "Vitamin B12", "Vitamin C", "Vitamin D"], 3,
             "UV-B rays in sunlight help the skin make Vitamin D, which is essential for absorbing calcium."),
            ("What is the SI unit of force?",
             ["Joule", "Watt", "Newton", "Pascal"], 2,
             "Force is measured in newtons (N). One newton accelerates 1 kg at 1 m/s²."),
            ("Which gas do plants take in during photosynthesis?",
             ["Oxygen", "Nitrogen", "Carbon dioxide", "Hydrogen"], 2,
             "Plants use carbon dioxide and water with sunlight to make glucose, releasing oxygen as a by-product."),
            ("Which is the largest organ of the human body?",
             ["Liver", "Skin", "Brain", "Lungs"], 1,
             "The skin is the largest organ by surface area and weight. The liver is the largest internal organ."),
            ("What is the pH of pure water at 25 °C?",
             ["5", "7", "9", "14"], 1,
             "Pure water is neutral, with a pH of 7. Values below 7 are acidic and values above 7 are basic."),
            ("What is the approximate speed of light in a vacuum?",
             ["3 × 10^5 m/s", "3 × 10^6 m/s", "3 × 10^8 m/s", "3 × 10^10 m/s"], 2,
             "Light travels at about 3 × 10^8 metres per second (roughly 3 lakh km per second) in a vacuum."),
            ("Which blood components help the blood to clot?",
             ["Red blood cells", "White blood cells", "Platelets", "Plasma proteins only"], 2,
             "Platelets (thrombocytes) gather at a wound and start the clotting process."),
        ],
    },
]


class Command(BaseCommand):
    help = "Load sample tests and a demo student account (idempotent)."

    @transaction.atomic
    def handle(self, *args, **options):
        created = 0
        for data in TESTS:
            subject, _ = Subject.objects.get_or_create(
                name=data["subject"],
                defaults={"slug": data["subject"].lower().replace(" ", "-")},
            )
            test, is_new = Test.objects.get_or_create(
                slug=data["slug"],
                defaults={
                    "subject": subject,
                    "title": data["title"],
                    "description": data["description"],
                    "duration_minutes": data["duration"],
                    "marks_per_question": data["marks"],
                    "negative_marks": data["negative"],
                    "is_published": True,
                },
            )
            if not is_new:
                continue
            created += 1
            for order, (text, options, correct, explanation) in enumerate(data["questions"], start=1):
                question = Question.objects.create(test=test, text=text, explanation=explanation, order=order)
                Choice.objects.bulk_create(
                    Choice(question=question, text=option, is_correct=(i == correct))
                    for i, option in enumerate(options)
                )

        User = get_user_model()
        if not User.objects.filter(username=DEMO_USERNAME).exists():
            User.objects.create_user(DEMO_USERNAME, password=DEMO_PASSWORD)
            self.stdout.write(f"Created demo user '{DEMO_USERNAME}'.")

        self.stdout.write(self.style.SUCCESS(f"Seeded {created} new test(s)."))
