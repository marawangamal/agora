// app/page.tsx - Simple server component
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

interface Job {
  job_id: number;
  status: string;
  command: string;
  group_name: string;
  depends_on: string[];
}

const DUMMY_JOBS: Job[] = [
  {
    job_id: 123456,
    status: 'RUNNING',
    command: 'jrun viz',
    group_name: 'group1',
    depends_on: ['job2', 'job3'],
  },
  {
    job_id: 789012,
    status: 'COMPLETED',
    command: 'jrun analyze',
    group_name: '',
    depends_on: [],
  },
];

// Server action to get jobs
export async function getJobs(): Promise<{ jobs: Job[]; error?: string }> {
    console.log('Running jrun viz...');
    const { stdout } = await execAsync('jrun viz --mode json');
    const data = JSON.parse(stdout);
    const jobs: Job[] = data.jobs
    
    // Simulate a delay for the async function
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    // Return dummy jobs for now
    return { jobs };
}
