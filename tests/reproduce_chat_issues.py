import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.response_builder import force_rewrite_to_tinglish

def test_ivanni_valla():
    print("Testing force_rewrite_to_tinglish for 'ivanni valla' artifact...")
    
    input_text = """
IVF (In Vitro Fertilization) is a type of fertility treatment that helps with fertilization. In this process, eggs and sperm are combined in a lab, and then the embryo is transferred to the woman's uterus. IVF is mostly recommended for couples due to:

- Blocked fallopian tubes: If fallopian tubes are blocked, conception becomes tough.
- Low sperm count: If sperm count is low, fertilization becomes a problem.
- Unexplained infertility: If infertility exists without known reasons, IVF is a good option.

See, don't worry, IVF gives good results.
"""

    output = force_rewrite_to_tinglish(input_text, user_name="Harini")
    
    with open("repro_output.txt", "w", encoding="utf-8") as f:
        f.write(output)
        f.write("\n\n")
        if "ivanni valla" in output.lower():
            f.write("FAILURE: 'ivanni valla' found in output.")
            print("FAILURE: 'ivanni valla' found in output.")
        else:
            f.write("SUCCESS: 'ivanni valla' NOT found in output.")
            print("SUCCESS: 'ivanni valla' NOT found in output.")

def test_konni_tips_ivvandi():
    print("\nTesting force_rewrite_to_tinglish for 'konni tips ivvandi' artifact...")
    
    input_text = """
Maintaining a healthy weight is very important for fertility. A Body Mass Index (BMI) of 18.5 to 24.9 is ideal for men and women. Being underweight or overweight can affect hormone levels and ovulation, making it difficult to conceive.

To achieve a healthy weight, a balanced diet, hydration, and regular exercise helps a lot. Here are some tips:

- Protein and Fiber: Eat more protein and fiber-rich foods.
- Sugar Intake: It is better to reduce sugar intake.
- Physical Activities: Include 30 minutes of physical activities like Yoga or walking in your day.
"""

    output = force_rewrite_to_tinglish(input_text, user_name="Harini")
    
    with open("repro_output.txt", "a", encoding="utf-8") as f:
        f.write("\n\n--- TEST 2: Konni Tips ---\n")
        f.write(output)
        f.write("\n\n")
        
        # Check for incorrect phrasing
        # "ivvandi" means "give (imperative form)", which is wrong when the bot is GIVING tips.
        if "ivvandi" in output.lower() or "ivvi" in output.lower():
            f.write("FAILURE: 'ivvandi' or 'ivvi' found in output.")
            print("FAILURE: 'ivvandi' or 'ivvi' found in output.")
        else:
            f.write("SUCCESS: 'ivvandi/ivvi' NOT found in output.")
            print("SUCCESS: 'ivvandi/ivvi' NOT found in output.")

if __name__ == "__main__":
    test_ivanni_valla()
    test_konni_tips_ivvandi()
