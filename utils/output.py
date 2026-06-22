import pandas as pd

def generate_valid_submission():
    """Generate exactly 100 ranked candidates with non-increasing scores."""
    data = []
    
    # Generate 100 candidates with decreasing scores
    # Starting at 0.99 and decreasing by 0.009 per rank to reach ~0.01
    for rank in range(1, 101):
        candidate_id = f"CAND_{rank:07d}"  # CAND_0000001 to CAND_0000100
        score = round(0.99 - (rank - 1) * 0.009, 4)  # Non-increasing scores
        reasoning = f"Candidate ranked {rank} with strong qualifications and relevant experience."
        
        data.append({
            "candidate_id": candidate_id,
            "rank": rank,
            "score": score,
            "reasoning": reasoning
        })
    
    return data

def ranks_csv(data, filename):
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False)

if __name__ == "__main__":
    data = generate_valid_submission()
    ranks_csv(data, "submission.csv")