export type Mastery = 'locked' | 'unlocked' | 'learning' | 'learned' | 'mastered'

export interface ResourceOut {
  kind: 'video' | 'reading' | 'link'
  title: string
  url: string
  note: string
}

export interface TopicNode {
  id: number
  slug: string
  title: string
  unit: string
  description: string
  est_minutes: number
  depth_rank: number
  mastery: Mastery
  prereq_ids: number[]
  has_lesson: boolean
  fsrs_due_at: string | null
}

export interface UnitOut {
  title: string
  topics: TopicNode[]
}

export interface CourseSummary {
  id: number
  slug: string
  title: string
  description: string
  level: string
  category: string
  document_id: number | null
  sequence_order: number
  source: string
  enrolled: boolean
  topic_count: number
  learned_count: number
  mastered_count: number
}

export interface CourseDetail extends CourseSummary {
  units: UnitOut[]
}

export interface WorkedExample {
  problem_md: string
  solution_md: string
}

export interface LessonOut {
  content_md: string
  worked_examples: WorkedExample[]
  source: string
}

export interface TopicDetail {
  id: number
  slug: string
  title: string
  unit: string
  description: string
  course_slug: string
  course_title: string
  est_minutes: number
  mastery: Mastery
  generator_keys: string[]
  lesson: LessonOut | null
  resources: ResourceOut[]
  prereqs: TopicNode[]
}

export interface AuthUser {
  id: number
  username: string | null
  name: string
}

export interface MeOut {
  require_auth: boolean
  user: AuthUser | null
}
