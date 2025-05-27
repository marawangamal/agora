"use client"

import React, { useEffect, useMemo, useRef, useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Progress } from "@/components/ui/progress"
import {
  Terminal,
  Clock,
  CheckCircle,
  XCircle,
  Pause,
  Users,
  GitBranch,
  Search,
  Filter,
  Cpu,
  HardDrive,
  Moon,
  Sun,
} from "lucide-react"

interface JobStats {
  gpu_memory_used_mb?: number
  gpu_memory_total_mb?: number
  gpu_count?: number
}

interface Job {
  job_id: number
  command: string
  preamble: string
  group_name: string
  depends_on: string[]
  status: string
  inactive_deps: string[]
  stats?: JobStats
}

// Fetch jobs via API
async function getJobs(): Promise<Job[]> {
  try {
    const response = await fetch(`/api/jobs${window.location.search}`)
    if (!response.ok) throw new Error("Failed to fetch jobs")
    return await response.json()
  } catch (error) {
    console.error("Error fetching jobs:", error)
    return []
  }
}

function getStatusIcon(status: string) {
  switch (status.toLowerCase()) {
    case "running":
      return <Clock className="w-4 h-4" />
    case "completed":
      return <CheckCircle className="w-4 h-4" />
    case "failed":
      return <XCircle className="w-4 h-4" />
    case "pending":
      return <Pause className="w-4 h-4" />
    default:
      return <Clock className="w-4 h-4" />
  }
}

function getStatusVariant(
  status: string
): "default" | "secondary" | "destructive" | "outline" {
  switch (status.toLowerCase()) {
    case "running":
      return "default"
    case "completed":
      return "secondary"
    case "failed":
      return "destructive"
    case "pending":
      return "outline"
    default:
      return "outline"
  }
}

function getStatusColor(status: string) {
  switch (status.toLowerCase()) {
    case "running":
      return "#3b82f6"
    case "completed":
      return "#10b981"
    case "failed":
      return "#ef4444"
    case "pending":
      return "#f59e0b"
    default:
      return "#6b7280"
  }
}

const smartRangeDisplay = (jobIds: number[]): string => {
  const sorted = [...jobIds].sort((a, b) => a - b)
  if (sorted.length === 1) return `${sorted[0]}`
  if (sorted.length <= 3) return sorted.join(", ")
  const isContinuous = sorted.every(
    (id, i) => i === 0 || id === sorted[i - 1] + 1
  )
  if (isContinuous) {
    return `${sorted[0]}-${sorted[sorted.length - 1]} (${sorted.length})`
  }
  return `${sorted[0]}...${sorted[sorted.length - 1]} (${sorted.length})`
}

export default function Component() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isDarkMode, setIsDarkMode] = useState(false)
  const [statusFilter, setStatusFilter] = useState("all")
  const [groupFilter, setGroupFilter] = useState("all")
  const [searchQuery, setSearchQuery] = useState("")

  useEffect(() => {
    setIsLoading(true)
    getJobs()
      .then((data) => setJobs(data))
      .catch((_) => {})
      .finally(() => setIsLoading(false))
  }, [])

  // Filtered jobs
  const filteredJobs = useMemo(
    () =>
      jobs.filter((job) => {
        const matchesStatus =
          statusFilter === "all" || job.status === statusFilter
        const matchesGroup =
          groupFilter === "all" || job.group_name === groupFilter
        const matchesSearch =
          searchQuery === "" ||
          job.command.toLowerCase().includes(searchQuery.toLowerCase()) ||
          job.job_id.toString().includes(searchQuery)
        return matchesStatus && matchesGroup && matchesSearch
      }),
    [jobs, statusFilter, groupFilter, searchQuery]
  )

  // Unique lists, filtering out any empty
  const uniqueStatuses = useMemo(
    () =>
      Array.from(
        new Set(jobs.map((j) => j.status).filter((s): s is string => !!s))
      ),
    [jobs]
  )
  const uniqueGroups = useMemo(
    () =>
      Array.from(
        new Set(
          jobs.map((j) => j.group_name).filter((g): g is string => !!g)
        )
      ),
    [jobs]
  )

  // Helper for group progress
  const getGroupStatus = (jobs: Job[]) => {
    if (jobs.every((j) => j.status === "COMPLETED")) return "COMPLETED"
    if (jobs.some((j) => j.status === "FAILED")) return "FAILED"
    if (jobs.some((j) => j.status === "RUNNING")) return "RUNNING"
    return "PENDING"
  }
  const getGroupProgress = (jobs: Job[]) => {
    const done = jobs.filter((j) => j.status === "COMPLETED").length
    return (done / jobs.length) * 100
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-4">
      <div className="max-w-7xl mx-auto space-y-6">
        <header className="flex justify-between items-center">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            SLURM Job Dashboard
          </h1>
          <button
            onClick={() => setIsDarkMode((d) => !d)}
            className="p-2 rounded bg-white dark:bg-gray-800"
          >
            {isDarkMode ? <Sun /> : <Moon />}
          </button>
        </header>

        {/* Filters */}
        <Card>
          <CardContent className="flex flex-wrap gap-4 items-center">
            <div className="flex items-center gap-2">
              <Search />
              <Input
                placeholder="Search jobs..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>

            <div className="flex items-center gap-2">
              <Filter />
              <Select
                value={statusFilter}
                onValueChange={(v) => setStatusFilter(v)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Statuses</SelectItem>
                  {uniqueStatuses.map((s) => (
                    <SelectItem key={s} value={s}>
                      {s}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center gap-2">
              <Users />
              <Select
                value={groupFilter}
                onValueChange={(v) => setGroupFilter(v)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Group" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Groups</SelectItem>
                  {uniqueGroups.map((g) => (
                    <SelectItem key={g} value={g}>
                      {g}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="text-sm text-gray-600 dark:text-gray-400">
              Showing {filteredJobs.length} of {jobs.length} jobs
            </div>
          </CardContent>
        </Card>

        {/* Graph */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><GitBranch /> Dependency Graph</CardTitle>
            <p className="text-sm text-gray-500">Click a group to see its jobs</p>
          </CardHeader>
          <CardContent>
            {/* You can render DependencyGraph here similarly */}
            {/* For brevity, omitting the SVG-based graph component */}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
