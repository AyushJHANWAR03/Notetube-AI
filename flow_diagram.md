# NoteTube AI - System Flow Diagram

```mermaid
flowchart TD
    %% Main Flow
    A[User] -->|1. Paste YouTube URL| B[Frontend]
    B -->|2. Send to Backend| C[Backend API]
    C -->|3. Validate & Create Job| D[(Database)]
    C -->|4. Queue Job| E[Redis Queue]
    F[Worker] -->|5. Process Job| E
    
    %% Video Processing Steps
    F -->|6. Get Video Info| G[YouTube API]
    F -->|7. Get Transcript| H[Supadata]
    F -->|8. Generate Content| I[OpenAI]
    F -->|9. Save Results| D
    
    %% Status Updates
    B -->|10. Poll Status| C
    C -->|11. Return Status| B
    B -->|12. Show Results| A

    %% Styling
    classDef user fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef frontend fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    classDef backend fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef database fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px
    classDef queue fill:#ffebee,stroke:#c62828,stroke-width:2px
    classDef external fill:#e0f7fa,stroke:#00838f,stroke-width:2px
    
    class A user
    class B frontend
    class C,D backend
    class E queue
    class F backend
    class G,H,I external
```

## Flow Explanation

### 1. User Submission
- User pastes a YouTube URL into the web interface
- Frontend sends the URL to the backend API

### 2. Job Creation
- Backend validates the URL
- Creates a job record in the database
- Adds the job to the processing queue

### 3. Background Processing
- Worker picks up the job from the queue
- Fetches video metadata from YouTube
- Gets transcript using Supadata
- Generates notes, chapters, and flashcards using OpenAI
- Saves all results to the database

### 4. Status Updates
- Frontend periodically checks job status
- Backend returns current processing state
- Progress is shown to the user

### 5. Completion
- When processing finishes, results are displayed
- User can interact with the generated content

## Components

- **Frontend**: Next.js web interface
- **Backend API**: FastAPI server
- **Database**: PostgreSQL for storage
- **Queue**: Redis for job management
- **Worker**: Background job processor
- **External Services**: YouTube, Supadata, OpenAI APIs

## Error Handling
- Failed jobs are logged and can be retried
- Users see clear error messages
- System handles rate limits and API failures gracefully
