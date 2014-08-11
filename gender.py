from collections import defaultdict
import string
import nltk
import sys


table = string.maketrans("","")
def no_punc(w):
    # N.B.: Will cause trouble with names containing punctuation
    return w.translate(table, string.punctuation)


def long_names(words, i):
    # This finds names longer than a single word and reports them back and how many skips
    # are needed to get to the proper next position.
    # N.B.: Middle initials not supported
    words.append(" ")
    skip_count = 0
    full_name = [words[i]]
    while words[i + skip_count][-1] not in string.punctuation and words[i + skip_count + 1].istitle():
        skip_count += 1
    return " ".join([no_punc(w) for w in words[i:i+skip_count+1]]), skip_count


def is_name(word, namebank, i, tags):
    # Checks whether the word in question is a part of speech which could possibly be a name
    # and if it matches a known name.
    return word in namebank and tags[i][1].startswith("NN")


def possible_names(s, namebank):
    # Extracts names based on matching a title or matching against a table of names.
    # Requires proper capitalization. Names which are not fully capitalized will not work properly.
    # e.g Pierre de la Harpe ==> Pierre vs. Pierre De La Harpe ==> Pierre De La Harpe
    # Also, Dr. Pepper.
    words = nltk.word_tokenize(s)
    names = []
    skip_count = 0
    pos_tags = nltk.pos_tag(nltk.word_tokenize(s))
    for i, word in enumerate(words):
        if word[0] == word[0].lower() or skip_count > 0:
            skip_count -= 1
            continue
        else:
            name = None
            if word in ["Ms.", "Mrs.", "Mr.", "Dr."]:
                name, skip_count = long_names(words, i + 1)
                skip_count += 1
                name = word + " " + name
            else:
                clean_w = no_punc(word)
                if is_name(clean_w, namebank, i, pos_tags):
                    name, skip_count = long_names(words,i)
            if name: names.append([name, i])
    return names


def build_namebank():
    # Loads census data with gender splits for each name (top 90% of names)
    names_male = open("dist.male.first")
    names_female = open("dist.female.first")
    names_dict = defaultdict(lambda: [0, 0])
    
    next_line = names_male.readline()
    while next_line:
        split_line = next_line.split()
        names_dict[split_line[0].title()][0] += float(split_line[1])
        next_line = next(names_male, None)
        
    next_line = names_female.readline()
    while next_line:
        split_line = next_line.split()
        names_dict[split_line[0].title()][1] += float(split_line[1])
        next_line = next(names_female, None)
        
    name_freqs = defaultdict(lambda: 0.49)
    for key in names_dict.keys():
        name_freqs[key] = names_dict[key][0] / (names_dict[key][0] + names_dict[key][1])
    return name_freqs, names_dict


def gender_by_context(i, words, namebank):
    # This seeks outward from the target word until it finds a gender indicating word and reports that gender back.
    # Looks for tiebreakers.
    # Will have trouble with Drs. with 2 first names e.g. Dr. William Ashley will be guessed as either
    # male or female depending on whether it is written Dr. William Ashley or Dr. Ashley
    if words[i] == "Dr." and words[i+1] in namebank.keys():
        return namebank[words[i+1]]
    gender_indicators = defaultdict(int)
    gender_indicators.update({"his": 1, "he": 1, "her": -1, "hers": -1, "she": -1})
    right = left = 0
    bounds = [-1 * i, len(words) - i - 1]
    gender = 0
    while (left > bounds[0] or right < bounds[1]) and gender == 0:
        left -= 1
        right += 1
        if left >= bounds[0]:
            gender += gender_indicators[words[i + left]]
        if right <= bounds[1]:
            gender += gender_indicators[words[i + right]]
    return 1 / (1 + 2.0**(-2.0 * gender))


def gender_by_title(title, i, words):
    # Chooses gender given title information
    if title == "Ms." or title == "Mrs.":
        if words[i + 1] == "Doubtfire":
            gender_odds = 1
        else:
            gender_odds = 0
    elif title == "Mr.":
        gender_odds = 1
    return gender_odds


def gender_by_name(name, namebank):
    # Simply checks against the loaded data. Could have been
    # executed as an expression but I pulled it out for consistency
    # with the other gender_by_* methods.
    return namebank[name[0].split()[0]]


def prob2gender(prob):
    if prob > 0.5:
        return "MALE"
    else:
        return "FEMALE"


def gender_guess(s, namebank, verbose = False):
    # Uses a very basic title or name lookup.
    names = possible_names(s, namebank)
    genders = []
    for name in names:
        if name[0][:4] in ["Ms. ", "Mrs.", "Mr. "]:
            prob = gender_by_title(name[0][:4].split()[0], name[1], nltk.word_tokenize(s))
        elif name[0][:3] == "Dr.":
            prob = gender_by_context(name[1], nltk.word_tokenize(s), namebank)
        else:
            prob = gender_by_name(name, namebank)
        genders.append({"name": name[0], "prob": prob, "gender": prob2gender(prob)}) 

    if verbose:
        for pair in genders:
            print "Name:  {0}".format(pair["name"]).ljust(50) + "Male Odds:  {0}".format(pair["prob"])
    return genders


def main(input_file, output_file):
	sentences = open(input_file).readlines()
	output = open(output_file, "w")
	namebank, r_namebank = build_namebank()
	for sentence in sentences:
		output.write(str([[x["name"], x["gender"]] for x in gender_guess(sentence, namebank)]) + "\n")
	output.close()


if __name__ == "__main__":
	if len(sys.argv) < 3:
		print "Use: >> python gender.py input_filename output_filename"
	else:
		input_file = sys.argv[1]
		output_file = sys.argv[2]
		main(input_file, output_file)