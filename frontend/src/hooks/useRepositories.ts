import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { RepositoriesApi, type ListRepositoriesParams } from "@/api/repositories";
import type { RepositoryCreateInput } from "@/types/api";

export const repositoryQueryKeys = {
  all: ["repositories"] as const,
  list: (params: ListRepositoriesParams) => [...repositoryQueryKeys.all, "list", params] as const,
  detail: (id: string) => [...repositoryQueryKeys.all, "detail", id] as const,
};

export function useRepositories(params: ListRepositoriesParams = {}) {
  return useQuery({
    queryKey: repositoryQueryKeys.list(params),
    queryFn: () => RepositoriesApi.list(params),
    placeholderData: keepPreviousData,
  });
}

export function useRepository(id: string | undefined) {
  return useQuery({
    queryKey: repositoryQueryKeys.detail(id ?? ""),
    queryFn: () => RepositoriesApi.get(id as string),
    enabled: Boolean(id),
  });
}

export function useCreateRepository() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: RepositoryCreateInput) => RepositoriesApi.create(input),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: repositoryQueryKeys.all });
    },
  });
}

export function useDeleteRepository() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => RepositoriesApi.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: repositoryQueryKeys.all });
    },
  });
}

export function useSetVisibility() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, isPublic }: { id: string; isPublic: boolean }) =>
      RepositoriesApi.setVisibility(id, isPublic),
    onSuccess: (repo) => {
      qc.setQueryData(repositoryQueryKeys.detail(repo.id), repo);
      qc.invalidateQueries({ queryKey: repositoryQueryKeys.all });
    },
  });
}
